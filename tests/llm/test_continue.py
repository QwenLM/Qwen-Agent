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


@pytest.mark.parametrize('stream', [True, False])
@pytest.mark.parametrize('delta_stream', [False])
@pytest.mark.parametrize('llm_cfg', [{
    'model': 'qwen-max',
    'model_server': 'dashscope'
}, {
    'model': 'qwen2.5-7b-instruct',
    'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'api_key': os.getenv('DASHSCOPE_API_KEY', 'none')
}])
def test_continue(stream, delta_stream, llm_cfg):
    if not stream and delta_stream:
        pytest.skip('Skipping this combination')

    # Chat with text llm
    llm = get_chat_model(llm_cfg)
    messages = [
        Message('user', 'what is 1+1?'),
        Message('assistant', '```python\nprint(1+1)\n```\n```output\n2\n```\n')
    ]
    # messages = [Message('user', 'hi'),
    #             Message('assistant', 'hi，今天天气')]

    response = llm.chat(messages=messages, stream=stream, delta_stream=delta_stream)
    if stream:
        response = list(response)[-1]
    assert isinstance(response[-1]['content'], str)
    assert response[-1].function_call is None
    print(response)


if __name__ == '__main__':
    test_continue(stream=True, delta_stream=False, llm_cfg={'model': 'qwen-max', 'model_server': 'dashscope'})
    test_continue(stream=True,
                  delta_stream=False,
                  llm_cfg={
                      'model': 'qwen2-7b-instruct',
                      'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                      'api_key': os.getenv('DASHSCOPE_API_KEY', 'none')
                  })
