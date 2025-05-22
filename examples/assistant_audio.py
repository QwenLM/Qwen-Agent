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
    bot = Assistant(llm={'model_type': 'qwenaudio_dashscope', 'model': 'qwen-audio-turbo-latest'})
    messages = [{
        'role':
            'user',
        'content': [{
            'audio': 'https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3'
        }, {
            'text': '这段音频在说什么?'
        }]
    }]
    for rsp in bot.run(messages):
        print(rsp)


def app_gui():
    # Define the agent
    bot = Assistant(llm={'model': 'qwen-audio-turbo-latest'})
    WebUI(bot).run()


if __name__ == '__main__':
    # test()
    app_gui()
