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

import json
import os

import pytest

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import Message

functions = [{
    'name': 'image_gen',
    'description': 'AI绘画（图像生成）服务，输入文本描述和图像分辨率，返回根据文本信息绘制的图片URL。',
    'parameters': {
        'type': 'object',
        'properties': {
            'prompt': {
                'type': 'string',
                'description': '详细描述了希望生成的图像具有什么内容，例如人物、环境、动作等细节描述，使用英文',
            },
        },
        'required': ['prompt'],
    }
}]


@pytest.mark.parametrize('functions', [None, functions])
@pytest.mark.parametrize('stream', [True, False])
@pytest.mark.parametrize('delta_stream', [True, False])
def test_llm_oai(functions, stream, delta_stream):
    if not stream and delta_stream:
        pytest.skip('Skipping this combination')

    if delta_stream and functions:
        pytest.skip('Skipping this combination')

    # settings
    llm_cfg = {
        'model': 'qwen2-7b-instruct',
        'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'api_key': os.getenv('DASHSCOPE_API_KEY', 'none')
    }

    llm = get_chat_model(llm_cfg)
    assert llm.max_retries == 0

    messages = [Message('user', 'draw a cute cat')]
    response = llm.chat(messages=messages, functions=functions, stream=stream, delta_stream=delta_stream)
    if stream:
        response = list(response)[-1]

    assert isinstance(response[-1]['content'], str)
    if functions:
        assert response[-1].function_call.name == 'image_gen'
    else:
        assert response[-1].function_call is None


@pytest.mark.parametrize('call_count', [1, 2])
@pytest.mark.parametrize('interleaved', [False, True])
def test_llm_oai_streamed_tool_calls_keep_arguments_by_index(monkeypatch, call_count, interleaved):
    ChatCompletionChunk = pytest.importorskip('openai.types.chat').ChatCompletionChunk
    cities = ['Paris', 'Tokyo'][:call_count]
    chunks = []

    def add_chunk(tool_calls):
        chunks.append(
            ChatCompletionChunk(id='test',
                                created=0,
                                model='local-model',
                                object='chat.completion.chunk',
                                choices=[{
                                    'index': 0,
                                    'delta': {
                                        'tool_calls': tool_calls
                                    }
                                }]))

    initial = [{
        'index': index,
        'id': f'call_{index}',
        'type': 'function',
        'function': {
            'name': 'get_weather',
            'arguments': '{"city":"'
        },
    } for index in range(call_count)]
    if interleaved:
        add_chunk(initial)
        add_chunk([{
            'index': index,
            'function': {
                'arguments': cities[index]
            },
        } for index in range(call_count - 1, -1, -1)])
        add_chunk([{'index': index, 'function': {'arguments': '"}'}} for index in range(call_count)])
    else:
        for index, tool_call in enumerate(initial):
            add_chunk([tool_call])
            add_chunk([{'index': index, 'function': {'arguments': cities[index] + '"}'}}])

    llm = get_chat_model({
        'model': 'local-model',
        'model_type': 'oai',
        'api_key': 'unused',
        'generate_cfg': {
            'use_raw_api': True
        },
    })
    monkeypatch.setattr(llm, '_chat_complete_create', lambda **kwargs: iter(chunks))

    response = list(llm.chat(messages=[Message('user', 'Check the weather')]))[-1]

    assert [msg.extra['function_id'] for msg in response] == [f'call_{index}' for index in range(call_count)]
    assert [msg.function_call.name for msg in response] == ['get_weather'] * call_count
    assert [json.loads(msg.function_call.arguments) for msg in response] == [{'city': city} for city in cities]
