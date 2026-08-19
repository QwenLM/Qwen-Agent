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

import os
from types import SimpleNamespace

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


def test_parallel_tool_call_chunks_are_merged_by_index():

    def tool_call(index, call_id=None, name=None, arguments=None):
        return SimpleNamespace(index=index, id=call_id, function=SimpleNamespace(name=name, arguments=arguments))

    def chunk(*tool_calls):
        delta = SimpleNamespace(content=None, reasoning_content=None, tool_calls=list(tool_calls))
        return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])

    chunks = [
        chunk(
            tool_call(0, call_id='call-weather', name='get_weather', arguments='{"city":"'),
            tool_call(1, call_id='call-time', name='get_time', arguments='{"zone":"'),
        ),
        chunk(
            tool_call(0, arguments='Paris"}'),
            tool_call(1, arguments='UTC"}'),
        ),
    ]
    llm = get_chat_model({'model': 'test', 'model_server': 'http://localhost/v1', 'api_key': 'EMPTY'})
    llm._chat_complete_create = lambda **kwargs: iter(chunks)

    responses = list(
        llm._chat_stream(
            messages=[Message(role='user', content='Run both tools')],
            delta_stream=False,
            generate_cfg={},
        ))

    tool_calls = [message for message in responses[-1] if message.function_call]
    assert [(message.function_call.name, message.function_call.arguments) for message in tool_calls] == [
        ('get_weather', '{"city":"Paris"}'),
        ('get_time', '{"zone":"UTC"}'),
    ]
    assert [message.extra['function_id'] for message in tool_calls] == ['call-weather', 'call-time']
