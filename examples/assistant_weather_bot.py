"""A weather forecast assistant implemented by assistant"""
import os
from typing import Optional

from qwen_agent.agents import Assistant

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')


def init_agent_service():
    llm_cfg = {'model': 'qwen-max'}
    system = (
        '你扮演一个天气预报助手，你具有查询天气和画图能力。'
        '你需要查询相应地区的天气，然后调用给你的画图工具绘制一张城市的图，并从给定的诗词文档中选一首相关的诗词来描述天气，不要说文档以外的诗词。')

    tools = ['image_gen', 'amap_weather']
    bot = Assistant(llm=llm_cfg, system_message=system, function_list=tools)

    return bot


def app():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []
    while True:
        # Query example: 海淀区天气
        query = input('user question: ')
        # File example: resource/poem.pdf
        file = input('file url (press enter if no file): ').strip()
        if not query:
            print('user question cannot be empty！')
            continue
        if not file:
            messages.append({'role': 'user', 'content': query})
        else:
            messages.append({
                'role': 'user',
                'content': [{
                    'text': query
                }, {
                    'file': file
                }]
            })

        response = []
        for response in bot.run(messages):
            print('bot response:', response)
        messages.extend(response)


def test(query='海淀区天气',
         file: Optional[str] = os.path.join(ROOT_RESOURCE, 'poem.pdf')):
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []

    if not file:
        messages.append({'role': 'user', 'content': query})
    else:
        messages.append({
            'role': 'user',
            'content': [{
                'text': query
            }, {
                'file': file
            }]
        })

    for response in bot.run(messages):
        print('bot response:', response)


if __name__ == '__main__':
    app()
