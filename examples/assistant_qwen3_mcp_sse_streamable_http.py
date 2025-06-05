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

"""A calculator assistant implemented by assistant"""

import os

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')

"""
# for this example, you need create a sse or streamable-http mcp server by fastmcp

from fastmcp import FastMCP

mcp = FastMCP("Demo")

@mcp.tool(description="Multiply two numbers")
def multiply(a: int, b: int) -> int:
    return a * b

if __name__ == "__main__":
    # mcp.run(transport="sse", host="127.0.0.1", port=8000)
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)

"""

def init_agent_service():
    # llm_cfg = {
    #     # Use the model service provided by DashScope:
    #     'model': 'qwen3-235b-a22b',
    #     'model_type': 'qwen_dashscope',
    # }
    llm_cfg = {
        # Use the OpenAI-compatible model service provided by ModelScope:
        'model': 'Qwen/Qwen3-8B',
        'model_server': 'https://api-inference.modelscope.cn/v1/',  # modelscope api_base
        'api_key': 'your token', # https://modelscope.cn/my/myaccesstoken
    }
    system = ('你扮演一个计算器\\no_think')
    tools = [{
        "mcpServers": {
            # "calculate-sse": {
            #     "type": "sse",
            #     "url": "http://127.0.0.1:8000/sse"
            # },
            "calculate-streamable-http": {
                "type": "streamable-http",
                "url": "http://127.0.0.1:8000/mcp"
            },
        }
    }]

    bot = Assistant(
        llm=llm_cfg,
        name='个人助手',
        description='个人助手',
        system_message=system,
        function_list=tools,
    )

    return bot

def test(query='1234乘以2345'):
    # Define the agent
    bot = init_agent_service()
    # Chat
    messages = []
    messages.append({'role': 'user', 'content': query})
    for response in bot.run(messages):
        print('bot response:', response)


def app_tui():
    # Define the agent
    bot = init_agent_service()
    # Chat
    messages = []
    while True:
        # Query example: 1234乘以2345
        query = input('user question: ')
        if not query:
            print('user question cannot be empty！')
            continue

        messages.append({'role': 'user', 'content': query})

        response = []
        for response in bot.run(messages):
            print('bot response:', response)
        messages.extend(response)


def app_gui():
    # Define the agent
    bot = init_agent_service()
    chatbot_config = {
        'prompt.suggestions': [
            '1234乘以2345',
            '1234加2345'
        ]
    }
    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()


if __name__ == '__main__':
    test()
    # app_tui()
    # app_gui()