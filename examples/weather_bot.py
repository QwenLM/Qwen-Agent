from qwen_agent.prompts import Assistant

# config
role = '你扮演一个天气预报助手，你需要查询相应地区的天气，同时调用给你的画图工具绘制一张城市的图。'
llm_config = {
    'model': 'qwen-max',
    'model_server': 'dashscope',
    'generate_cfg': {
        'top_p': 0.8
    }
}
function_list = ['image_gen', 'amap_weather']

# init agent
bot = Assistant(function_list=function_list,
                llm=llm_config,
                system_message=role)

messages = []
while True:
    # input query
    print('\n\n=====User input====:')
    query = input()
    messages.append({'role': 'user', 'content': query})

    # run agent
    response_stream = bot.run(messages=messages)

    # result processing
    print('\n=====Bot====:')
    response = []
    for response in response_stream:
        print(response)

    messages.extend(response)
