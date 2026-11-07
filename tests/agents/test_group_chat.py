import copy
import socket

import pytest

from qwen_agent.agents.fncall_agent import FnCallAgent
from qwen_agent.agents.group_chat import GroupChat
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import FunctionCall, Message
from qwen_agent.tools import BaseTool


class ScriptedModel(BaseChatModel):
    """Keep the model boundary offline while running the real agent/tool workflow."""

    def __init__(self, responses):
        super().__init__({'model': 'offline-test'})
        self.responses = iter(responses)
        self.requests = []

    def chat(self, messages, **kwargs):
        self.requests.append(copy.deepcopy(messages))
        yield copy.deepcopy(next(self.responses))

    def _chat_with_functions(self, *args, **kwargs):
        raise AssertionError('Unexpected provider call')

    def _chat_stream(self, *args, **kwargs):
        raise AssertionError('Unexpected provider call')

    def _chat_no_stream(self, *args, **kwargs):
        raise AssertionError('Unexpected provider call')


class EchoTool(BaseTool):
    name = 'echo'
    description = 'Return a private tool result.'
    parameters = []

    def call(self, params, **kwargs):
        return f'private tool result: {params}'


class OtherEchoTool(EchoTool):
    name = 'other_echo'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):

    def fail(*args, **kwargs):
        raise AssertionError('These tests must not contact a model service')

    monkeypatch.setattr(socket.socket, 'connect', fail)


def call(identifier, tool_name='echo'):
    return Message('assistant',
                   f'Calling tool {identifier}',
                   function_call=FunctionCall(tool_name, '{"value": "%s"}' % identifier),
                   extra={'function_id': identifier})


def make_chat(responses):
    alice_model = ScriptedModel(responses)
    bob_model = ScriptedModel([[Message('assistant', 'Bob is done')]])
    alice = FnCallAgent(name='Alice', llm=alice_model, function_list=[EchoTool(), OtherEchoTool()])
    bob = FnCallAgent(name='Bob', llm=bob_model)
    chat = GroupChat(agents=[alice, bob], agent_selection_method='round_robin')
    return chat, alice_model, bob_model


@pytest.mark.parametrize('as_dict', [False, True])
@pytest.mark.parametrize('second_tool', ['echo', 'other_echo'])
def test_parallel_calls_handoff_to_next_agent(as_dict, second_tool):
    calls = [call('first'), call('second', second_tool)]
    chat, alice_model, bob_model = make_chat([calls, [Message('assistant', 'Alice is done')]])
    messages = [Message('user', 'Please work together')]
    if as_dict:
        messages = [m.model_dump() for m in messages]
    original = copy.deepcopy(messages)

    response = list(chat.run(messages, max_round=2))[-1]

    assert messages == original
    if as_dict:
        response = [Message(**m) for m in response]
    assert [m.role for m in response] == ['assistant', 'assistant', 'function', 'function', 'assistant', 'assistant']
    assert response[-1].name == 'Bob'
    assert [m.extra['function_id'] for m in response[:4]] == ['first', 'second', 'first', 'second']
    assert len(alice_model.requests) == 2
    assert len(bob_model.requests) == 1
    context = '\n'.join(str(m.content) for m in bob_model.requests[0])
    assert 'Alice: Calling tool first' in context
    assert 'Alice: Calling tool second' in context
    assert 'Alice: Alice is done' in context
    assert 'private tool result' not in context
    assert all(m.role != 'function' and not m.function_call for m in bob_model.requests[0])


def test_parallel_calls_preserved_when_same_agent_resumes():
    chat, alice_model, bob_model = make_chat([[call('first'), call('second')], [Message('assistant', 'Alice is done')],
                                              [Message('assistant', 'Alice resumed')]])
    messages = [Message('user', 'First request')]
    first_response = list(chat.run(messages, max_round=1))[-1]
    messages += first_response + [Message('user', 'Continue')]
    original = copy.deepcopy(messages)

    response = list(chat.run(messages, max_round=1, mentioned_agents_name=['Alice']))[-1]

    assert messages == original
    assert response[-1].content == 'Alice resumed'
    assert bob_model.requests == []
    replay = alice_model.requests[-1]
    tool_messages = [m for m in replay if m.function_call or m.role == 'function']
    assert tool_messages == first_response[:4]
    assert [m.extra['function_id'] for m in tool_messages] == ['first', 'second', 'first', 'second']


@pytest.mark.parametrize('responses', [
    [[call('first')], [Message('assistant', 'Alice is done')]],
    [[call('first')], [call('second')], [Message('assistant', 'Alice is done')]],
    [[Message('assistant', 'Alice is done')]],
])
def test_single_sequential_and_plain_text_handoff(responses):
    chat, _, bob_model = make_chat(responses)

    response = list(chat.run([Message('user', 'Start')], max_round=2))[-1]

    assert response[-1].content == 'Bob is done'
    context = '\n'.join(str(m.content) for m in bob_model.requests[0])
    assert 'Alice: Alice is done' in context
    assert 'private tool result' not in context


@pytest.mark.parametrize('speaker', ['Alice', 'Bob'])
def test_missing_tool_result_still_rejected(speaker):
    chat, _, _ = make_chat([])
    incomplete = [
        Message('assistant', '', name='Alice', function_call=FunctionCall('echo', '{}')),
        Message('assistant', 'Finished', name='Alice')
    ]

    with pytest.raises(AssertionError):
        chat._manage_messages(incomplete, speaker)
