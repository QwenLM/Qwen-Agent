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

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI


def test():
    bot = Assistant(llm={'model': 'qwen-plus-latest'})
    messages = [{'role': 'user', 'content': [{'text': '介绍图一'}, {'file': 'https://arxiv.org/pdf/1706.03762.pdf'}]}]
    for rsp in bot.run(messages):
        print(rsp)


def app_gui():
    # Define the agent
    bot = Assistant(llm={'model': 'qwen-plus-latest'},
                    name='Assistant',
                    description='使用RAG检索并回答，支持文件类型：PDF/Word/PPT/TXT/HTML。')
    chatbot_config = {
        'prompt.suggestions': [
            {
                'text': '介绍图一'
            },
            {
                'text': '第二章第一句话是什么？'
            },
        ]
    }
    WebUI(bot, chatbot_config=chatbot_config).run()


if __name__ == '__main__':
    # test()
    app_gui()
