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

import pytest
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessage

from qwen_agent.llm.oai import TextChatAtOAI


def make_model(monkeypatch):
    model = TextChatAtOAI({'model': 'offline-control', 'api_key': 'test-only', 'generate_cfg': {'use_raw_api': False}})
    requests = []

    def create(**kwargs):
        requests.append(copy.deepcopy(kwargs))
        return iter([
            ChatCompletionChunk(id='local',
                                created=0,
                                model='offline-control',
                                object='chat.completion.chunk',
                                choices=[{
                                    'index': 0,
                                    'delta': {
                                        'content': 'Local answer'
                                    },
                                    'finish_reason': None,
                                }])
        ])

    monkeypatch.setattr(model, '_chat_complete_create', create)
    return model, requests


@pytest.mark.parametrize('count', [1, 2])
@pytest.mark.parametrize('content_mode', ['omitted', 'null', 'text'])
@pytest.mark.parametrize('with_tools', [False, True])
def test_quick_chat_oai_tool_history(monkeypatch, count, content_mode, with_tools):
    model, requests = make_model(monkeypatch)
    calls = [{
        'id': f'call_{i}',
        'type': 'function',
        'function': {
            'name': 'echo',
            'arguments': '{}'
        }
    } for i in range(count)]
    assistant = ChatCompletionMessage(role='assistant', content=None, tool_calls=calls).model_dump(exclude_none=True)
    if content_mode == 'null':
        assistant['content'] = None
    elif content_mode == 'text':
        assistant['content'] = 'Checking local results.'
    messages = [{'role': 'user', 'content': 'Echo locally.'}, assistant]
    messages.extend({
        'role': 'tool',
        'tool_call_id': call['id'],
        'name': 'echo',
        'content': f'observation_{i}'
    } for i, call in enumerate(calls))
    messages.append({'role': 'user', 'content': 'Summarize the local observations.'})
    tools = [{
        'type': 'function',
        'function': {
            'name': 'echo',
            'description': 'Local echo',
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        }
    }] if with_tools else None
    original, original_tools = copy.deepcopy(messages), copy.deepcopy(tools)

    result = list(model.quick_chat_oai(messages, tools=tools))

    assert result[-1]['choices'][0]['message']['content'] == 'Local answer'
    assert len(requests) == 1
    assert requests[0]['stream'] is True
    assert requests[0]['model'] == 'offline-control'
    wire_text = str(requests[0]['messages'])
    assert all(f'observation_{i}' in wire_text for i in range(count))
    assert ('echo' in wire_text)
    assert messages == original
    assert tools == original_tools


def test_quick_chat_oai_plain_text(monkeypatch):
    model, requests = make_model(monkeypatch)
    messages = [{'role': 'user', 'content': 'Hello locally.'}]
    original = copy.deepcopy(messages)

    assert list(model.quick_chat_oai(messages))[-1]['choices'][0]['message']['content'] == 'Local answer'
    assert requests[0]['messages'][-1]['content'] == 'Hello locally.'
    assert messages == original


@pytest.mark.parametrize('tool_calls', [None, []])
def test_quick_chat_oai_invalid_missing_content(monkeypatch, tool_calls):
    model, requests = make_model(monkeypatch)
    assistant = {'role': 'assistant'}
    if tool_calls is not None:
        assistant['tool_calls'] = tool_calls
    messages = [{'role': 'user', 'content': 'Hello'}, assistant]
    original = copy.deepcopy(messages)

    with pytest.raises(KeyError, match='content'):
        list(model.quick_chat_oai(messages))
    assert requests == []
    assert messages == original
