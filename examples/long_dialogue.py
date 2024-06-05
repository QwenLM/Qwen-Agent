from qwen_agent.agents import DialogueRetrievalAgent
from qwen_agent.gui import WebUI


def test():
    # Define the agent
    bot = DialogueRetrievalAgent(llm={'model': 'qwen-max'})

    # Chat
    long_text = '，'.join(['这是干扰内容'] * 1000 + ['小明的爸爸叫大头'] + ['这是干扰内容'] * 1000)
    messages = [{'role': 'user', 'content': f'小明爸爸叫什么？\n{long_text}'}]

    for response in bot.run(messages):
        print('bot response:', response)


def app_tui():
    bot = DialogueRetrievalAgent(llm={'model': 'qwen-max'})

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
    # Define the agent
    bot = DialogueRetrievalAgent(llm={'model': 'qwen-max'})

    WebUI(bot).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
