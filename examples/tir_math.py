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

"""A TIR(tool-integrated reasoning) math agent
```bash
python tir_math.py
```
"""
import os
from pprint import pprint

from qwen_agent.agents import TIRMathAgent
from qwen_agent.gui import WebUI

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')

# We use the following two systems to distinguish between COT mode and TIR mode
TIR_SYSTEM = """Please integrate natural language reasoning with programs to solve the problem above, and put your final answer within \\boxed{}."""
COT_SYSTEM = """Please reason step by step, and put your final answer within \\boxed{}."""


def init_agent_service():
    # Use this to access the qwen2.5-math model deployed on dashscope
    llm_cfg = {'model': 'qwen2.5-math-72b-instruct', 'model_type': 'qwen_dashscope', 'generate_cfg': {'top_k': 1}}
    bot = TIRMathAgent(llm=llm_cfg, name='Qwen2.5-Math', system_message=TIR_SYSTEM)
    return bot


def test(query: str = '斐波那契数列前10个数字'):
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = [{'role': 'user', 'content': query}]
    for response in bot.run(messages):
        pprint(response, indent=2)


def app_tui():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []
    while True:
        # Query example: 斐波那契数列前10个数字
        query = input('user question: ')
        messages.append({'role': 'user', 'content': query})
        response = []
        for response in bot.run(messages):
            print('bot response:', response)
        messages.extend(response)


def app_gui():
    bot = init_agent_service()
    chatbot_config = {
        'prompt.suggestions': [
            r'曲线 $y=2 \\ln (x+1)$ 在点 $(0,0)$ 处的切线方程为 $( )$.',
            'A digital display shows the current date as an $8$-digit integer consisting of a $4$-digit year, '
            'followed by a $2$-digit month, followed by a $2$-digit date within the month. '
            'For example, Arbor Day this year is displayed as 20230428. '
            'For how many dates in $2023$ will each digit appear an even number of times '
            'in the 8-digital display for that date?'
        ]
    }
    WebUI(bot, chatbot_config=chatbot_config).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
