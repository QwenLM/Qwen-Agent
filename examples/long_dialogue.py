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

from qwen_agent.agents import DialogueRetrievalAgent
from qwen_agent.gui import WebUI


def test():
    # Define the agent
    bot = DialogueRetrievalAgent(llm={'model': 'qwen-max'})

    # Chat
    long_text = '，'.join(['这是干扰内容'] * 1000 + ['小明的爸爸叫大头'] + ['这是干扰内容'] * 1000)
    messages = [{'role': 'user', 'content': f'小明爸爸叫什么？\n{long_text}'}]

    for response in bot.run(messages):
        print('bot response:', response)


def app_tui():
    bot = DialogueRetrievalAgent(llm={'model': 'qwen-max'})

    # Chat
    messages = []
    while True:
        query = input('user question: ')
        messages.append({'role': 'user', 'content': query})
        response = []
        for response in bot.run(messages=messages):
            print('bot response:', response)
        messages.extend(response)


def app_gui():
    # Define the agent
    bot = DialogueRetrievalAgent(llm={'model': 'qwen-max'})

    WebUI(bot).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
