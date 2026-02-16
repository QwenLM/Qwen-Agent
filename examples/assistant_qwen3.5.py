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
"""An agent implemented by assistant with qwen3.5"""
import os  # noqa

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
from qwen_agent.utils.output_beautify import typewriter_print


def init_agent_service():
    llm_cfg = {
        # Use the OpenAI-compatible model service provided by DashScope:
        'model': 'qwen3.5-plus',
        'model_type': 'qwenvl_oai',
        'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'api_key': os.getenv('DASHSCOPE_API_KEY'),
        'generate_cfg': {
            'use_raw_api': True,
            # When using Dash Scope OAI API, pass the parameter of whether to enable thinking mode in this way
            'extra_body': {
                'enable_thinking': True
            },
        },
    }
    # llm_cfg = {
    #     # Use your own model service compatible with OpenAI API by vLLM/SGLang:
    #     'model': 'Qwen/Qwen3.5-397B-A17B',
    #     'model_type': 'qwenvl_oai',
    #     'model_server': 'http://localhost:8000/v1',  # api_base
    #     'api_key': 'EMPTY',
    #
    #     'generate_cfg': {
    #         'use_raw_api': True,
    #         # When using vLLM/SGLang OAI API, pass the parameter of whether to enable thinking mode in this way
    #         'extra_body': {
    #             'chat_template_kwargs': {'enable_thinking': True}
    #         },
    #     },
    # }
    tools = [{
        'mcpServers': {  # You can specify the MCP configuration file
            'time': {
                'command': 'uvx',
                'args': ['mcp-server-time', '--local-timezone=Asia/Shanghai']
            },
            'fetch': {
                'command': 'uvx',
                'args': ['mcp-server-fetch']
            },
            'filesystem': {
                'command': 'npx',
                'args': ['-y', '@modelcontextprotocol/server-filesystem', '/path/to/allowed/files']
            }
        }
    }]
    bot = Assistant(
        llm=llm_cfg,
        function_list=tools,
        name='Qwen3.5 Tool-calling Demo',
        description="I'm a demo using the Qwen3.5 tool calling. Welcome to add and play with your own tools!")

    return bot


def test(query: str = 'What time is it?'):
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
    chatbot_config = {
        'prompt.suggestions': [
            'Help me organize my desktop.',
            'Develop a dog website and save it on the desktop',
        ]
    }
    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
