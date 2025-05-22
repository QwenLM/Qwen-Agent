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
