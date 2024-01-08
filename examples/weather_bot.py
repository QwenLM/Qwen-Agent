from qwen_agent.prompts import RolePlay

# config
role = '你扮演一个天气预报助手，你需要查询相应地区的天气，同时调用给你的画图工具绘制一张城市的图。'
llm_config = {'model': 'qwen-max', 'api_key': '', 'model_server': 'dashscope'}
function_list = ['image_gen', 'amap_weather']

# init agent
bot = RolePlay(function_list=function_list,
               llm=llm_config,
               system_instruction=role)

# run agent
response = bot.run('朝阳区天气')

# result processing
text = ''
for chunk in response:
    text += chunk
print(text)
