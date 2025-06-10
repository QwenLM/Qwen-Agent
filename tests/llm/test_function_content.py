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


@pytest.mark.parametrize('cfg', [0, 1])
@pytest.mark.parametrize('gen_cfg1', [
    None,
    dict(parallel_function_calls=True),
    dict(function_choice='auto'),
    dict(function_choice='none'),
    dict(function_choice='get_current_weather'),
])
@pytest.mark.parametrize('gen_cfg2', [
    None,
    dict(function_choice='none'),
    dict(function_choice='get_current_weather'),
])
def test_function_content(cfg, gen_cfg1, gen_cfg2):
    if cfg == 0:
        llm = get_chat_model({
            # Use the model service provided by DashScope:
            'model': 'qwen2.5-7b-instruct',
            'model_server': 'dashscope',
            'api_key': os.getenv('DASHSCOPE_API_KEY'),
            'generate_cfg': {
                'fncall_prompt_type': 'qwen'
            },
        })
    else:
        llm = get_chat_model({
            'model': 'qwen2.5-7b-instruct',
            'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'api_key': os.getenv('DASHSCOPE_API_KEY', 'none'),
            'generate_cfg': {
                'fncall_prompt_type': 'qwen'
            },
        })

    # Step 1: send the conversation and available functions to the model
    messages = [{'role': 'user', 'content': "What's the weather like in San Francisco?"}]
    functions = [{
        'name': 'get_current_weather',
        'description': 'Get the current weather in a given location',
        'parameters': {
            'type': 'object',
            'properties': {
                'location': {
                    'type': 'string',
                    'description': 'The city and state, e.g. San Francisco, CA',
                },
                'unit': {
                    'type': 'string',
                    'enum': ['celsius', 'fahrenheit']
                },
            },
            'required': ['location'],
        },
    }]

    print('# Assistant Response 1:')
    responses = []
    for responses in llm.chat(messages=messages, functions=functions, stream=True, extra_generate_cfg=gen_cfg1):
        print(responses)

    messages.extend(responses)  # extend conversation with assistant's reply

    if gen_cfg1 and (gen_cfg1.get('function_choice') == 'none'):
        assert all([('function_call' not in rsp) for rsp in responses])
        return

    # Step 2: check if the model wanted to call a function
    last_response = messages[-1]
    assert last_response.get('function_call')
    messages.append({
        'role': 'function',
        'name': last_response['function_call']['name'],
        'content': '',
    })

    print('# Assistant Response 2:')
    for responses in llm.chat(
            messages=messages,
            functions=functions,
            stream=True,
            extra_generate_cfg=gen_cfg2,
    ):  # get a new response from the model where it can see the function response
        print(responses)


if __name__ == '__main__':
    test_function_content(0)
    test_function_content(1)
