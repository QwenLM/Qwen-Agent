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
from types import SimpleNamespace

import pytest

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.oai import TextChatAtOAI
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


def test_llm_oai_preserves_usage_no_stream():
    llm = TextChatAtOAI({'model': 'test-model', 'api_key': 'test-key'})
    usage = {'prompt_tokens': 3, 'completion_tokens': 5, 'total_tokens': 8}
    llm._chat_complete_create = lambda **kwargs: SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='hello'))],
        usage=usage,
    )

    response = llm._chat_no_stream([Message('user', 'hi')], {})

    assert response[0].content == 'hello'
    assert response[0].extra == {'model_service_info': {'usage': usage}}
    json.dumps(response[0].model_dump())


def test_llm_oai_preserves_final_stream_usage():
    llm = TextChatAtOAI({'model': 'test-model', 'api_key': 'test-key'})
    usage = {'prompt_tokens': 3, 'completion_tokens': 5, 'total_tokens': 8}
    llm._chat_complete_create = lambda **kwargs: iter([
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content='hello'))], usage=None),
        SimpleNamespace(choices=[], usage=usage),
    ])

    responses = list(llm._chat_stream([Message('user', 'hi')], delta_stream=False, generate_cfg={}))

    assert responses[-1][0].content == 'hello'
    assert responses[-1][0].extra == {'model_service_info': {'usage': usage}}
    json.dumps(responses[-1][0].model_dump())
