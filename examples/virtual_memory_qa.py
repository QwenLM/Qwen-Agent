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

"""A retrieval docqa assistant implemented by virtual memory agent"""

import os

from qwen_agent.agents import VirtualMemoryAgent
from qwen_agent.gui import WebUI

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')


def init_agent_service():
    llm_cfg = {'model': 'qwen-max'}
    system = '一个文档问答助手。'
    bot = VirtualMemoryAgent(
        llm=llm_cfg,
        system_message=system,
    )

    return bot


def test(query='简单列出这篇文章的贡献https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf',):
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = [{'role': 'user', 'content': query}]

    for response in bot.run(messages):
        print('bot response:', response)


def app_tui():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []
    while True:
        # Query example: 简单列出这篇文章的贡献https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf
        query = input('user question: ')
        # File example: resource/poem.pdf
        file = input('file url (press enter if no file): ').strip()
        if not query:
            print('user question cannot be empty！')
            continue
        if not file:
            messages.append({'role': 'user', 'content': query})
        else:
            messages.append({'role': 'user', 'content': [{'text': query}, {'file': file}]})

        response = []
        for response in bot.run(messages):
            print('bot response:', response)
        messages.extend(response)


def app_gui():
    # Define the agent
    bot = init_agent_service()
    chatbot_config = {
        'prompt.suggestions': ['简单列出这篇文章的贡献https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf']
    }

    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
