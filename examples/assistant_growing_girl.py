"""A girl's growth story novelist implemented by assistant"""
import os
from typing import Optional

from qwen_agent.agents import Assistant

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')


def init_agent_service():
    llm_cfg = {'model': 'qwen-max'}
    tools = ['image_gen']
    bot = Assistant(llm=llm_cfg,
                    function_list=tools,
                    system_message='你扮演一个漫画家，根据我给你的女孩的不同阶段，使用工具画出每个阶段女孩的的图片，'
                    '并串成一个故事讲述出来。要求图片背景丰富')
    return bot


def app():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []
    while True:
        # Query example: 请用image_gen开始创作！
        query = input('user question: ')
        # File example: resource/growing_girl.pdf
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


def test(query='请用image_gen开始创作！',
         file: Optional[str] = os.path.join(ROOT_RESOURCE,
                                            'growing_girl.pdf')):
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
