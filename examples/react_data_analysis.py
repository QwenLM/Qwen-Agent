"""A data analysis example implemented by assistant"""
import os
from typing import Optional

from qwen_agent.agents import ReActChat

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')


def init_agent_service():
    llm_cfg = {
        # 'model': 'Qwen/Qwen1.5-72B-Chat',
        # 'model_server': 'https://api.together.xyz',
        # 'api_key': os.getenv('TOGETHER_API_KEY'),
        'model': 'qwen-max',
        'model_server': 'dashscope',
        'api_key': os.getenv('DASHSCOPE_API_KEY'),
    }
    tools = ['code_interpreter']
    bot = ReActChat(llm=llm_cfg, function_list=tools)
    return bot


def app():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []
    while True:
        # Query example: pd.head the file first and then help me draw a line chart to show the changes in stock prices
        query = input('user question: ')
        # File example: resource/stock_prices.csv
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
    query:  # noqa
    str = 'pd.head the file first and then help me draw a line chart to show the changes in stock prices',
    file: Optional[str] = os.path.join(ROOT_RESOURCE,
                                       'stock_prices.csv')):  # noqa
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
