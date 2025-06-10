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
import urllib.parse

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import ContentItem
from qwen_agent.utils.utils import save_url_to_local_work_dir


def image_gen(prompt: str) -> str:
    prompt = urllib.parse.quote(prompt)
    image_url = f'https://image.pollinations.ai/prompt/{prompt}'
    image_url = save_url_to_local_work_dir(image_url, save_dir='./', save_filename='pic.jpg')
    return image_url


def test():
    # Config for the model
    llm_cfg_oai = {
        # Using Qwen2-VL deployed at any openai-compatible service such as vLLM:
        # 'model_type': 'qwenvl_oai',
        # 'model': 'Qwen2-VL-7B-Instruct',
        # 'model_server': 'http://localhost:8000/v1',  # api_base
        # 'api_key': 'EMPTY',

        # Using Qwen2-VL provided by Alibaba Cloud DashScope's openai-compatible service:
        # 'model_type': 'qwenvl_oai',
        # 'model': 'qwen-vl-max-0809',
        # 'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        # 'api_key': os.getenv('DASHSCOPE_API_KEY'),

        # Using Qwen2-VL provided by Alibaba Cloud DashScope:
        'model_type': 'qwenvl_dashscope',
        'model': 'qwen-vl-max-0809',
        'api_key': os.getenv('DASHSCOPE_API_KEY'),
        'generate_cfg': {
            'max_retries': 10,
            'fncall_prompt_type': 'qwen'
        }
    }
    llm = get_chat_model(llm_cfg_oai)

    # Initial conversation
    messages = [{
        'role':
            'user',
        'content': [{
            'image': 'https://dashscope.oss-cn-beijing.aliyuncs.com/images/dog_and_girl.jpeg'
        }, {
            'text': '图片中的内容是什么？请画一张内容相同，风格类似的图片。把女人换成男人'
        }]
    }]

    functions = [
        {
            'name': 'image_gen',
            'description': 'AI绘画（图像生成）服务，输入文本描述，返回根据文本信息绘制的图片URL。',
            'parameters': {
                'name': 'prompt',
                'type': 'string',
                'description': '详细描述了希望生成的图像具有什么内容，例如人物、环境、动作等细节描述，使用英文',
                'required': True
            }
        },
    ]

    print('# Assistant Response 1:')
    responses = []
    for responses in llm.chat(messages=messages, functions=functions, stream=True):
        print(responses)
    messages.extend(responses)

    for rsp in responses:
        if rsp.get('function_call', None):
            func_name = rsp['function_call']['name']
            if func_name == 'image_gen':
                func_args = json.loads(rsp['function_call']['arguments'])
                image_url = image_gen(func_args['prompt'])
                print('# Function Response:')
                func_rsp = {
                    'role': 'function',
                    'name': func_name,
                    'content': [ContentItem(image=image_url),
                                ContentItem(text=f'（ 这张图片的URL是 {image_url} ）')],
                }
                messages.append(func_rsp)
                print(func_rsp)
            else:
                raise NotImplementedError

    print('# Assistant Response 2:')
    responses = []
    for responses in llm.chat(messages=messages, functions=functions, stream=True):
        print(responses)
    messages.extend(responses)


if __name__ == '__main__':
    test()
