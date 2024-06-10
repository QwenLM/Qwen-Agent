"""A comfort game implemented by assistant"""

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI


def init_agent_service():
    llm_cfg = {'model': 'qwen-max'}
    system = ('我们来玩角色扮演游戏。你扮演用户的女友。由用户开始发言，根据他的发言，你初始化一个心情值（0到100）并作出回应。'
              '用户的任务是哄你开心，你根据每次用户说的话调整心情，每次回复开头加上（当前心情：分数）。')

    bot = Assistant(llm=llm_cfg, name='虚拟女友', description='哄哄机器人', system_message=system)

    return bot


def test(query: str = '你今天真好看'):
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = [{'role': 'user', 'content': query}]
    for response in bot.run(messages=messages):
        print('bot response:', response)


def app_tui():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []
    while True:
        query = input('user question: ')
        messages.append({'role': 'user', 'content': query})
        response = []
        for response in bot.run(messages=messages):
            print('bot response:', response)
        messages.extend(response)


def app_gui():
    agent = init_agent_service()
    chatbot_config = {
        'prompt.suggestions': [
            '你今天真好看！',
            '晚上去吃好吃的嘛~',
            '宝贝，你又瘦啦！',
        ]
    }
    WebUI(agent, chatbot_config=chatbot_config).run(messages=[{'role': 'assistant', 'content': [{'text': '还不快来哄哄我！'}]}])


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
