"""A data analysis example implemented by assistant"""
import os

from qwen_agent.agents import ReActChat


def init_agent_service():
    # settings
    llm_cfg = {
        'model': 'Qwen/Qwen1.5-72B-Chat',
        'model_server': 'https://api.together.xyz',
        'api_key': os.getenv('TOGETHER_API_KEY'),

        # 'model': 'qwen-max',
        # 'model_server': 'dashscope',
        # 'api_key': os.getenv('DASHSCOPE_API_KEY'),
    }
    tools = ['code_interpreter']
    bot = ReActChat(llm=llm_cfg, function_list=tools)
    return bot


def app():
    # define the agent
    bot = init_agent_service()

    # chat
    messages = []
    while True:
        # query example: pd.head the file first and then help me draw a line chart to show the changes in stock prices
        query = input('user question: ')
        # file example: resource/stock_prices.csv
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


if __name__ == '__main__':
    app()
