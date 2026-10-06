# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import socket
from types import SimpleNamespace

import pytest

from qwen_agent.llm.base import _truncate_input_messages_roughly
from qwen_agent.llm.oai import TextChatAtOAI
from qwen_agent.llm.schema import ContentItem, FunctionCall, Message
from qwen_agent.utils.tokenization_qwen import tokenizer
from qwen_agent.utils.utils import extract_text_from_message


@pytest.fixture(autouse=True)
def disable_network(monkeypatch):

    def reject_network(*args, **kwargs):
        raise AssertionError('These tests must not contact a model provider or other network service.')

    monkeypatch.setattr(socket, 'create_connection', reject_network)
    monkeypatch.setattr(socket, 'getaddrinfo', reject_network)
    monkeypatch.setattr(socket.socket, 'connect', reject_network)
    monkeypatch.setattr(socket.socket, 'connect_ex', reject_network)
    monkeypatch.setattr('openai.OpenAI', reject_network, raising=False)


def tool_messages(earlier_result=False, content_items=False):
    content = 'report data ' * 100
    if content_items:
        content = [ContentItem(text='report data ' * 50), ContentItem(text='report data ' * 50)]
    messages = [
        Message(role='user', content='Read the report.'),
        Message(role='assistant',
                content='',
                function_call=FunctionCall(name='read_report', arguments='{}'),
                extra={'function_id': 'call_report'}),
        Message(role='function',
                content=content,
                name='read_report',
                extra={
                    'function_id': 'call_report',
                    'source': {
                        'pages': [1, 2]
                    }
                }),
    ]
    if earlier_result:
        messages.append(Message(role='assistant', content='I have read the report.'))
    return messages


@pytest.mark.parametrize('earlier_result', [False, True], ids=['latest', 'earlier'])
@pytest.mark.parametrize('content_items', [False, True], ids=['string', 'text_items'])
def test_truncated_tool_result_preserves_metadata(earlier_result, content_items):
    messages = tool_messages(earlier_result, content_items)
    before = copy.deepcopy(messages)

    result = _truncate_input_messages_roughly(messages, max_tokens=100)
    tool_result = next(msg for msg in result if msg.role == 'function')

    assert messages == before
    assert isinstance(tool_result.content, str)
    assert tokenizer.count_tokens(tool_result.content) < tokenizer.count_tokens('report data ' * 100)
    assert tool_result.name == before[2].name
    assert tool_result.extra == before[2].extra
    assert result[:2] == before[:2]
    assert result[3:] == before[3:]
    assert result[1].function_call is not messages[1].function_call
    assert tool_result is not messages[2]
    assert tool_result.extra is not messages[2].extra
    assert tool_result.extra['source'] is not messages[2].extra['source']
    tool_result.extra['source']['pages'].append(3)
    tool_result.content = 'changed output'
    assert messages == before


@pytest.mark.parametrize('earlier_result', [False, True], ids=['latest', 'earlier'])
@pytest.mark.parametrize('content_items', [False, True], ids=['string', 'text_items'])
def test_large_budget_leaves_tool_messages_unchanged(earlier_result, content_items):
    messages = tool_messages(earlier_result, content_items)
    before = copy.deepcopy(messages)

    result = _truncate_input_messages_roughly(messages, max_tokens=10000)

    assert result == before
    assert messages == before


@pytest.mark.parametrize('max_tokens', [100, 10000], ids=['truncated', 'untruncated'])
@pytest.mark.parametrize('content_items', [False, True], ids=['string', 'text_items'])
def test_chat_preserves_tool_result_id_with_fake_transport(monkeypatch, max_tokens, content_items):
    model = TextChatAtOAI({
        'model': 'offline-test',
        'model_type': 'oai',
        'api_key': 'EMPTY',
        'generate_cfg': {
            'use_raw_api': True,
            'max_input_tokens': max_tokens
        },
    })
    captured = []

    def fake_create(**kwargs):
        captured.append(kwargs['messages'])
        delta = SimpleNamespace(content='done', reasoning_content=None, tool_calls=None)
        return iter([SimpleNamespace(choices=[SimpleNamespace(delta=delta)])])

    monkeypatch.setattr(model, '_chat_complete_create', fake_create)
    messages = tool_messages(content_items=content_items)
    before = copy.deepcopy(messages)

    response = list(model.chat(messages=messages, stream=True))

    assert response[-1][-1].content == 'done'
    assert messages == before
    assert len(captured) == 1
    request = captured[0]
    assistant_call = next(msg for msg in request if msg['role'] == 'assistant')
    tool_result = next(msg for msg in request if msg['role'] == 'tool')
    # Accept either wire-field spelling; this test concerns preservation of the identifier value.
    result_id = tool_result.get('tool_call_id', tool_result.get('id'))
    assert assistant_call['tool_calls'][0]['id'] == result_id == 'call_report'
    assert tool_result['name'] == 'read_report'
    assert tool_result['extra'] == before[2].extra
    if max_tokens == 100:
        assert tokenizer.count_tokens(tool_result['content']) < tokenizer.count_tokens('report data ' * 100)
    else:
        assert tool_result['content'].count('report data') == 100
    tool_result['extra']['source']['pages'].append(3)
    assert messages == before


@pytest.mark.parametrize('role', ['user', 'assistant'])
def test_non_tool_truncation_keeps_existing_behavior(role):
    message = Message(role=role,
                      content='report data ' * 100,
                      name='speaker',
                      reasoning_content=[ContentItem(text='reasoning')],
                      extra={'source': {
                          'pages': [1, 2]
                      }})
    messages = [message] if role == 'user' else [Message(role='user', content='Read report.'), message]
    before = copy.deepcopy(messages)

    result = _truncate_input_messages_roughly(messages, max_tokens=100)

    assert messages == before
    assert result[-1].role == role
    assert tokenizer.count_tokens(result[-1].content) <= 100
    assert result[-1].content != message.content
    assert result[-1].name is None
    assert result[-1].extra is None
    assert result[-1].reasoning_content is None
    assert result[-1].function_call is None


def test_oversized_assistant_call_keeps_existing_budget_behavior():
    messages = [
        Message(role='user', content='Read report.'),
        Message(role='assistant',
                content='dispatch details ' * 100,
                function_call=FunctionCall(name='read_report',
                                           arguments='{"report": "' + 'large arguments ' * 100 + '"}'),
                reasoning_content='reasoning',
                name='speaker',
                extra={'function_id': 'call_report'}),
    ]
    before = copy.deepcopy(messages)
    assert tokenizer.count_tokens(str(messages[-1].function_call)) > 100

    result = _truncate_input_messages_roughly(messages, max_tokens=100)

    assert messages == before
    # Retaining this oversized call while truncating only content would defeat the existing token budget.
    assert result[-1].function_call is None
    assert result[-1].reasoning_content is None
    assert result[-1].name is None
    assert result[-1].extra is None
    assert sum(tokenizer.count_tokens(extract_text_from_message(msg, add_upload_info=True)) for msg in result) <= 100


def test_truncated_tool_result_only_adds_routing_metadata():
    messages = tool_messages()
    messages[2].reasoning_content = 'not a tool result field'
    messages[2].function_call = FunctionCall(name='not_a_tool_result', arguments='{}')
    before = copy.deepcopy(messages)

    result = _truncate_input_messages_roughly(messages, max_tokens=100)
    tool_result = next(msg for msg in result if msg.role == 'function')

    assert messages == before
    assert tool_result.name == 'read_report'
    assert tool_result.extra == before[2].extra
    assert tool_result.reasoning_content is None
    assert tool_result.function_call is None
    assistant_call = result[1]
    assert assistant_call == before[1]
    assert assistant_call.function_call is not messages[1].function_call
    assistant_call.function_call.arguments = '{"changed": true}'
    assert messages == before
