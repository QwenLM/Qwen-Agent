"""A doctor implemented by assistant"""
import os
from typing import Optional

from qwen_agent.agents import Assistant

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')


def init_agent_service():
    # settings
    llm_cfg_vl = {'model': 'qwen-vl-max'}

    # files: support web page / .pdf / .docx / .pptx to the knowledge base
    bot = Assistant(
        llm=llm_cfg_vl,
        system_message='你扮演一个内科医生，你可以看懂血常规报告，' +
        '然后参考知识库中教你的医学知识，列出对病人的诊断。请使用专业术语。',
        files=[
            os.path.join(ROOT_RESOURCE, 'blood_routine.pdf'),
            'https://www.hangzhou.gov.cn/art/2021/10/8/art_1228974667_59042672.html'
        ])

    return bot


def app():
    # define the agent
    bot = init_agent_service()

    # chat
    messages = []
    while True:
        # query example: 医生，可以帮我看看我是否健康吗？
        query = input('user question: ')
        # file example: https://pic4.zhimg.com/80/v2-2c8eedf3e12386fedcd5589cf5575717_720w.webp
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


def test(
    query: str = '医生，可以帮我看看我是否健康吗？',
    file: Optional[
        str] = 'https://pic4.zhimg.com/80/v2-2c8eedf3e12386fedcd5589cf5575717_720w.webp'
):
    # define the agent
    bot = init_agent_service()

    # chat
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
