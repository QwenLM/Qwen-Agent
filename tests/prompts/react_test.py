from qwen_agent.prompts import ReAct

# config
llm_config = {'model': 'qwen-max', 'api_key': '', 'model_server': 'dashscope'}
function_list = ['image_gen', 'code_interpreter']

# init agent
bot = ReAct(function_list=function_list, llm=llm_config)

messages = []

query = '画个折线图'
messages.append({'role': 'user', 'content': query})

# run agent
response_stream = bot.run(messages=messages)

# result processing
print('\n=====Bot====:')
for response in response_stream:
    print(response)
