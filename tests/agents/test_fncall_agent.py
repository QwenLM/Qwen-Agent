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
import json
from types import SimpleNamespace
from unittest.mock import Mock

import dashscope
import pytest

from qwen_agent.agents import Assistant, FnCallAgent
from qwen_agent.llm.base import ModelServiceError
from qwen_agent.llm.oai import TextChatAtOAI
from qwen_agent.llm.qwen_dashscope import QwenChatAtDS
from qwen_agent.llm.schema import Message
from qwen_agent.tools.base import BaseTool


class CountingTool(BaseTool):
    name = 'counting_tool'
    description = 'Return a fixed observation.'
    parameters = []

    def __init__(self):
        super().__init__()
        self.calls = 0

    def call(self, params, **kwargs):
        assert json.loads(params) == {}
        self.calls += 1
        return 'observation'


def make_chunk(content=None, tool_calls=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


@pytest.fixture(params=[FnCallAgent, Assistant])
def agent(request):
    model = TextChatAtOAI({'model': 'offline-model', 'api_key': 'unused', 'generate_cfg': {'use_raw_api': False}})
    return request.param(llm=model, function_list=[CountingTool()])


@pytest.fixture(params=[False, True], ids=['prompt-tools', 'native-tools'])
def use_raw_api(request, agent):
    agent.llm.use_raw_api = request.param
    return request.param


@pytest.fixture(params=['run', 'run_nonstream'])
def run_agent(request):

    def run(agent, messages):
        if request.param == 'run':
            return list(agent.run(messages))[-1]
        return agent.run_nonstream(messages)

    return run


@pytest.fixture(params=['no-chunks', 'empty-delta', 'no-choices'])
def empty_chunks(request):
    if request.param == 'no-chunks':
        return []
    if request.param == 'empty-delta':
        return [make_chunk()]
    return [SimpleNamespace(choices=[])]


def tool_chunks(use_raw_api, count=1):
    if use_raw_api:
        calls = [
            SimpleNamespace(id=f'call-{i}', function=SimpleNamespace(name='counting_tool', arguments='{}'))
            for i in range(1, count + 1)
        ]
        return [make_chunk(tool_calls=calls)]
    return [make_chunk(content='<tool_call>{"name": "counting_tool", "arguments": {}}</tool_call>' * count)]


def test_empty_round_stops_without_repeating_request(agent, use_raw_api, run_agent, empty_chunks, monkeypatch):
    create = Mock(side_effect=lambda **kwargs: iter(empty_chunks))
    monkeypatch.setattr(agent.llm, '_chat_complete_create', create)
    messages = [{'role': 'user', 'content': 'Hello'}]

    assert run_agent(agent, messages) == []
    assert create.call_count == 1
    assert agent.function_map['counting_tool'].calls == 0
    assert messages == [{'role': 'user', 'content': 'Hello'}]


def test_empty_round_preserves_completed_tool_result(agent, use_raw_api, run_agent, empty_chunks, monkeypatch):
    calls = []

    def create(**kwargs):
        calls.append(copy.deepcopy(kwargs['messages']))
        return iter(tool_chunks(use_raw_api) if len(calls) == 1 else empty_chunks)

    monkeypatch.setattr(agent.llm, '_chat_complete_create', create)
    messages = [Message(role='user', content='Use the tool')]
    response = run_agent(agent, messages)

    assert len(calls) == 2
    assert len(response) == 2
    assert response[0].function_call.name == 'counting_tool'
    assert response[1].role == 'function'
    assert response[1].name == 'counting_tool'
    assert response[1].content == 'observation'
    assert response[1].extra['function_id'] == response[0].extra['function_id']
    assert 'observation' in json.dumps(calls[1])
    assert agent.function_map['counting_tool'].calls == 1
    assert messages == [Message(role='user', content='Use the tool')]


def test_tool_round_still_continues_to_answer(agent, use_raw_api, run_agent, monkeypatch):
    create = Mock(side_effect=[iter(tool_chunks(use_raw_api)), iter([make_chunk(content='Done')])])
    monkeypatch.setattr(agent.llm, '_chat_complete_create', create)
    response = run_agent(agent, [{'role': 'user', 'content': 'Use the tool'}])

    assert create.call_count == 2
    assert agent.function_map['counting_tool'].calls == 1
    assert [message['role'] for message in response] == ['assistant', 'function', 'assistant']
    assert response[1]['content'] == 'observation'
    assert response[2]['content'] == 'Done'


def test_empty_chunks_after_text_do_not_end_round_early(agent, use_raw_api, run_agent, monkeypatch):
    chunks = [make_chunk(), make_chunk(content='Hello'), make_chunk(), SimpleNamespace(choices=[])]
    create = Mock(side_effect=lambda **kwargs: iter(chunks))
    monkeypatch.setattr(agent.llm, '_chat_complete_create', create)
    response = run_agent(agent, [{'role': 'user', 'content': 'Hello'}])

    assert create.call_count == 1
    assert len(response) == 1
    assert response[0]['content'] == 'Hello'


def test_empty_round_preserves_parallel_tool_results(agent, use_raw_api, run_agent, monkeypatch):
    calls = []

    def create(**kwargs):
        calls.append(copy.deepcopy(kwargs['messages']))
        return iter(tool_chunks(use_raw_api, count=2) if len(calls) == 1 else [])

    monkeypatch.setattr(agent.llm, '_chat_complete_create', create)
    response = run_agent(agent, [Message(role='user', content='Use the tool twice')])

    assert len(calls) == 2
    assert [message.role for message in response] == ['assistant', 'assistant', 'function', 'function']
    call_ids = [message.extra['function_id'] for message in response[:2]]
    result_ids = [message.extra['function_id'] for message in response[2:]]
    assert call_ids == result_ids
    assert len(set(call_ids)) == 2
    assert all(message.content == 'observation' for message in response[2:])
    assert agent.function_map['counting_tool'].calls == 2


def test_model_service_error_is_not_silenced(agent, use_raw_api, run_agent, monkeypatch):
    create = Mock(side_effect=ModelServiceError(code='400', message='model request failed'))
    monkeypatch.setattr(agent.llm, '_chat_complete_create', create)

    with pytest.raises(ModelServiceError, match='model request failed'):
        run_agent(agent, [{'role': 'user', 'content': 'Hello'}])

    assert create.call_count == 1
    assert agent.function_map['counting_tool'].calls == 0


def test_dashscope_empty_round_stops(agent, use_raw_api, run_agent, monkeypatch):
    monkeypatch.setattr(dashscope, 'api_key', 'unused')
    agent.llm = QwenChatAtDS({
        'model': 'qwen-plus',
        'api_key': 'unused',
        'generate_cfg': {
            'use_raw_api': use_raw_api
        },
    })
    create = Mock(side_effect=lambda *args, **kwargs: iter([]))
    monkeypatch.setattr(dashscope.Generation, 'call', create)

    assert run_agent(agent, [{'role': 'user', 'content': 'Hello'}]) == []
    assert create.call_count == 1
    assert agent.function_map['counting_tool'].calls == 0
