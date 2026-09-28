# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest.mock import Mock

import pytest
from openai.types.chat import ChatCompletionChunk

from qwen_agent.agents import ReActChat
from qwen_agent.llm.oai import TextChatAtOAI
from qwen_agent.llm.schema import Message
from qwen_agent.tools import BaseTool


class EchoTool(BaseTool):
    name = 'echo'
    description = 'Echo text.'
    parameters = [{'name': 'text', 'type': 'string', 'required': True}]

    def __init__(self):
        super().__init__()
        self.inputs = []

    def call(self, params, **kwargs):
        text = self._verify_json_format_args(params)['text']
        self.inputs.append(text)
        return text


def chunk(content=None):
    return ChatCompletionChunk(id='test',
                               created=0,
                               model='test',
                               object='chat.completion.chunk',
                               choices=[{
                                   'index': 0,
                                   'delta': {
                                       'content': content
                                   },
                                   'finish_reason': 'stop' if content is None else None,
                               }])


def make_agent(monkeypatch, rounds):
    model = TextChatAtOAI({'model': 'test', 'api_key': 'test-only', 'generate_cfg': {'use_raw_api': False}})
    create = Mock(side_effect=[iter(chunks) for chunks in rounds])
    monkeypatch.setattr(model, '_chat_complete_create', create)
    tool = EchoTool()
    return ReActChat(llm=model, function_list=[tool]), tool, create


def run_agent(agent, nonstream):
    messages = [Message(role='user', content='Echo hello.')]
    if nonstream:
        return agent.run_nonstream(messages)
    return list(agent.run(messages))[-1]


@pytest.mark.parametrize('nonstream', [False, True], ids=['stream', 'nonstream'])
@pytest.mark.parametrize('empty_chunks', [[], [chunk()]], ids=['no-chunks', 'no-content'])
def test_react_empty_first_response(monkeypatch, nonstream, empty_chunks):
    agent, tool, create = make_agent(monkeypatch, [empty_chunks])

    assert run_agent(agent, nonstream) == []
    assert tool.inputs == []
    assert create.call_count == 1


@pytest.mark.parametrize('nonstream', [False, True], ids=['stream', 'nonstream'])
@pytest.mark.parametrize('empty_chunks', [[], [chunk()]], ids=['no-chunks', 'no-content'])
def test_react_empty_response_preserves_tool_observation(monkeypatch, nonstream, empty_chunks):
    action = 'Use echo.\nAction: echo\nAction Input: {"text": "hello"}'
    agent, tool, create = make_agent(monkeypatch, [[chunk(action)], empty_chunks])

    result = run_agent(agent, nonstream)

    assert len(result) == 1
    assert result[0].content == 'Thought: ' + action + '\nObservation: hello\nThought: '
    assert tool.inputs == ['hello']
    assert create.call_count == 2


def test_react_nonempty_response_keeps_streaming_and_final_answer(monkeypatch):
    action = 'Use echo.\nAction: echo\nAction Input: {"text": "hello"}'
    agent, tool, create = make_agent(monkeypatch, [[chunk(action)], [chunk('Final Answer: '), chunk('hello'), chunk()]])

    responses = list(agent.run([Message(role='user', content='Echo hello.')]))
    prefix = 'Thought: ' + action + '\nObservation: hello\nThought: '

    assert [response[0].content for response in responses] == [
        'Thought: ' + action,
        prefix,
        prefix + 'Final Answer: ',
        prefix + 'Final Answer: hello',
        prefix + 'Final Answer: hello',
    ]
    assert tool.inputs == ['hello']
    assert create.call_count == 2
