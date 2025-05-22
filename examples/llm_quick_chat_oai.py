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

"""An example of calling text llm interfaces by OpenAI-compatible interface"""
from qwen_agent.llm import get_chat_model


def test():
    llm_cfg = {'model': 'qwen-max', 'model_server': 'dashscope'}
    tools = [{
        'type': 'function',
        'function': {
            'name':
                'image_gen',
            'description':
                'AI painting (image generation) service, input text description and image resolution, and return the URL of the image drawn based on the text information.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'prompt': {
                        'type':
                            'string',
                        'description':
                            'Detailed description of the desired content of the generated image, such as details of characters, environment, actions, etc., in English.',
                    },
                },
                'required': ['prompt'],
            }
        }
    }]

    # Chat with text llm
    llm = get_chat_model(llm_cfg)
    messages = [{'role': 'user', 'content': '你是？'}]
    """
    llm.quick_chat_oai
        This is a temporary OpenAI-compatible interface that is encapsulated and may change at any time.
        It is mainly used for temporary interfaces and should not be overly dependent.
        - Only supports full streaming
        - The message is in dict format
        - Only supports text LLM
    """
    response = llm.quick_chat_oai(messages)
    for x in response:
        print(x)
    messages.append(x['choices'][0]['message'])

    messages.append({'role': 'user', 'content': '画个可爱小猫'})
    response = llm.quick_chat_oai(messages, tools=tools)
    for x in response:
        print(x)
    messages.append(x['choices'][0]['message'])

    # Simulation function call results
    messages.append({
        'role': 'tool',
        'name': 'image_gen',
        'content': '![fig-001](https://seopic.699pic.com/photo/60098/4947.jpg_wh1200.jpg)'
    })
    response = llm.quick_chat_oai(messages, tools=tools)
    for x in response:
        print(x)


if __name__ == '__main__':
    test()
