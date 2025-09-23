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
"""An agent implemented by assistant with qwenvl"""

import os

from qwen_agent.agents import FnCallAgent


def init_agent_service():
    llm_cfg = {
        'model_type': 'qwenvl_dashscope',
        'model': 'qwen3-vl-plus',
        'api_key': os.getenv('DASHSCOPE_API_KEY'),
    }

    tools = [
        'image_zoom_in_tool',
        'image_search',
        'web_search',
    ]
    bot = FnCallAgent(
        llm=llm_cfg,
        function_list=tools,
        name='QwenVL Agent Demo',
        system_message='',
    )

    return bot


def test(pic_url: str, query: str):
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = [{
        'role': 'user',
        'content': [
            {
                'image': pic_url
            },
            {
                'text': query
            },
        ]
    }]

    response = list(bot.run(messages=messages))[-1]
    print(response)
    bot.run(messages=messages)

    response_plain_text = response[-1]['content']
    print('\n\nFinal Response:\n', response_plain_text)


if __name__ == '__main__':
    test('https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg',
         '告诉我这只狗的品种')
