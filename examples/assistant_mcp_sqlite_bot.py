"""A sqlite database assistant implemented by assistant"""

import os
import asyncio
from typing import Optional

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')


def init_agent_service():
    llm_cfg = {'model': 'qwen-max'}
    system = ('你扮演一个数据库助手，你具有查询数据库的能力')
    tools = [{
        "mcpServers": {
            "sqlite" : {
                "command": "uvx",
                "args": [
                    "mcp-server-sqlite",
                    "--db-path",
                    "test.db"
                ]
            }
        }
    }]
    bot = Assistant(
        llm=llm_cfg,
        name='数据库助手',
        description='数据库查询',
        system_message=system,
        function_list=tools,
    )

    return bot


def test(query='数据库里有几张表', file: Optional[str] = os.path.join(ROOT_RESOURCE, 'poem.pdf')):
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []

    if not file:
        messages.append({'role': 'user', 'content': query})
    else:
        messages.append({'role': 'user', 'content': [{'text': query}, {'file': file}]})

    for response in bot.run(messages):
        print('bot response:', response)


def app_tui():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []
    while True:
        # Query example: 数据库里有几张表
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
        'prompt.suggestions': [
            '数据库里有几张表',
            '创建一个学生表包括学生的姓名、年龄',
            '增加一个学生名字叫韩梅梅，今年6岁',
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
