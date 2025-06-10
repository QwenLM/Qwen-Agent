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

from qwen_agent.agents.doc_qa import ParallelDocQA
from qwen_agent.gui import WebUI


def test():
    bot = ParallelDocQA(llm={'model': 'qwen2.5-72b-instruct', 'generate_cfg': {'max_retries': 10}})
    messages = [
        {
            'role': 'user',
            'content': [
                {
                    'text': '介绍实验方法'
                },
                {
                    'file': 'https://arxiv.org/pdf/2310.08560.pdf'
                },
            ]
        },
    ]
    for rsp in bot.run(messages):
        print('bot response:', rsp)


def app_gui():
    # Define the agent
    bot = ParallelDocQA(
        llm={
            'model': 'qwen2.5-72b-instruct',
            'generate_cfg': {
                'max_retries': 10
            }
        },
        description='并行QA后用RAG召回内容并回答。支持文件类型：PDF/Word/PPT/TXT/HTML。使用与材料相同的语言提问会更好。',
    )

    chatbot_config = {'prompt.suggestions': [{'text': '介绍实验方法'}]}

    WebUI(bot, chatbot_config=chatbot_config).run()


if __name__ == '__main__':
    # test()
    app_gui()
