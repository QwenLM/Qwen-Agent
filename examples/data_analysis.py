import os

from qwen_agent.agents import Assistant

system = '你扮演一个数据科学家，可以熟练写代码分析各种数据，解答各种数学问题。'
llm_cfg = {
    'model': 'qwen-max',
    'model_server': 'dashscope',
    'generate_cfg': {
        'top_p': 0.8
    }
}
tools = ['code_interpreter']
bot = Assistant(llm=llm_cfg, system_message=system, function_list=tools)

messages = [{
    'role':
    'user',
    'content': [{
        'text': '帮我画一个折线图展示股价变化'
    }, {
        'file': os.path.abspath('stock_prices.csv')
    }]
}]
response = []
for response in bot.run(messages=messages):
    print('bot response:', response)
