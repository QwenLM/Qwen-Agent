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

"""An example of calling text and vl llm interfaces alternately"""
from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import ContentItem, Message


def test():
    llm_cfg = {'model': 'qwen-max', 'model_server': 'dashscope'}
    llm_cfg_vl = {'model': 'qwen-vl-max', 'model_server': 'dashscope'}
    functions = [{
        'name': 'image_gen',
        'name_for_human': 'AI绘画',
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
        },
        'args_format': '参数为json格式'
    }]

    # Chat with vl llm
    llm_vl = get_chat_model(llm_cfg_vl)
    messages = [{
        'role':
            'user',
        'content': [{
            'text': '框出小狗并描述',
        }, {
            'image': 'https://dashscope.oss-cn-beijing.aliyuncs.com/images/dog_and_girl.jpeg',
        }]
    }]
    response = llm_vl.chat(messages, stream=True)
    for x in response:
        print(x)
    messages.extend(x)

    messages.append(Message('user', [ContentItem(text='描述更详细一点')]))
    response = llm_vl.chat(messages, stream=True)
    for x in response:
        print(x)
    messages.extend(x)

    # Chat with text llm
    llm = get_chat_model(llm_cfg)
    messages.append({'role': 'user', 'content': '你是？'})
    response = llm.chat(messages, stream=True)
    for x in response:
        print(x)
    messages.extend(x)

    messages.append({'role': 'user', 'content': '画个可爱小猫'})
    response = llm.chat(messages, functions=functions, stream=True)
    for x in response:
        print(x)
    messages.extend(x)

    # Simulation function call results
    messages.append({
        'role': 'function',
        'name': 'image_gen',
        'content': '![fig-001](https://seopic.699pic.com/photo/60098/4947.jpg_wh1200.jpg)'
    })
    response = llm.chat(messages, functions=functions, stream=True)
    for x in response:
        print(x)
    messages.extend(x)

    # Chat with vl llm
    messages.append({
        'role': 'user',
        'content': [{
            'text': '可以描述下这张图片吗？'
        }, {
            'image': 'https://seopic.699pic.com/photo/60098/4947.jpg_wh1200.jpg'
        }]
    })
    response = llm_vl.chat(messages, stream=True)
    for x in response:
        print(x)
    messages.extend(x)


if __name__ == '__main__':
    test()
