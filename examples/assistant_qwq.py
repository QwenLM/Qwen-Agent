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

"""An image generation agent implemented by assistant with qwq"""

import os

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
from qwen_agent.utils.output_beautify import typewriter_print

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')


def init_agent_service():
    llm_cfg = {
        'model': 'qwq-32b',
        'model_type': 'qwen_dashscope',
        'generate_cfg': {
            'fncall_prompt_type': 'nous',

            # This parameter needs to be passed in when the deployed model is an reasoning model (e.g. qwq-32b) and *does not* support the reasoning_content field (e.g. deploying qwq-32b directly with an old version of vLLM)
            # Add: When the content is `<think>this is the thought</think>this is the answer`
            # Do not add: When the response has been separated by reasoning_content and content
            # This parameter will affect the parsing strategy of tool call
            # 'thought_in_content': True,
        },
    }
    tools = [
        'image_gen',
        # 'web_search',  # Apply for an apikey here (https://serper.dev) and set it as an environment variable by `export SERPER_API_KEY=xxxxxx`
    ]
    bot = Assistant(
        llm=llm_cfg,
        function_list=tools,
        name='QwQ-32B Tool-calling Demo',
        description="I'm a demo using the QwQ-32B tool calling. Welcome to add and play with your own tools!")

    return bot


def test(query: str = '画一只猫，再画一只狗，最后画他们一起玩的画面，给我三张图'):
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = [{'role': 'user', 'content': query}]
    response_plain_text = ''
    for response in bot.run(messages=messages):
        response_plain_text = typewriter_print(response, response_plain_text)


def app_tui():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []
    while True:
        query = input('user question: ')
        messages.append({'role': 'user', 'content': query})
        response = []
        response_plain_text = ''
        for response in bot.run(messages=messages):
            response_plain_text = typewriter_print(response, response_plain_text)
        messages.extend(response)


def app_gui():
    # Define the agent
    bot = init_agent_service()
    chatbot_config = {'prompt.suggestions': ['画一只猫，再画一只狗，最后画他们一起玩的画面，给我三张图']}
    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
