"""A comfort game implemented by assistant"""
from qwen_agent.agents import Assistant


def create_agent():
    # settings
    llm_cfg = {'model': 'qwen-max'}
    system = ('我们来玩角色扮演游戏。你扮演用户的女友。由用户开始发言，根据他的发言，你初始化一个心情值（0到100）并作出回应。'
              '用户的任务是哄你开心，你根据每次用户说的话调整心情，每次回复开头加上（当前心情：分数）。')

    bot = Assistant(llm=llm_cfg, system_message=system)

    return bot


def main():
    # define the agent
    bot = create_agent()

    # chat
    messages = []
    while True:
        query = input('user question: ')
        messages.append({'role': 'user', 'content': query})
        response = []
        for response in bot.run(messages=messages):
            print('bot response:', response)
        messages.extend(response)


if __name__ == '__main__':
    main()
