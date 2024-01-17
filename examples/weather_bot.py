import json
import os
import urllib.parse

import json5

from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool

llm_cfg = {
    # 如果使用DashScope提供的模型服务：
    'model': 'qwen-max',
    'model_server': 'dashscope',
    # 如果使用自行部署的OpenAI API模型服务：
    # 'model': 'Qwen',
    # 'model_server': 'http://127.0.0.1:7905/v1',

    # （可选）模型的推理超参：
    'generate_cfg': {
        'top_p': 0.8
    }
}
system = '你扮演一个天气预报助手，你具有查询天气和画图能力。' + \
          '你需要查询相应地区的天气，然后调用给你的画图工具绘制一张城市的图，并从给定的诗词文档中选一首相关的诗词来描述天气，不要说文档以外的诗词。'


# 增加一个名为my_image_gen的自定义工具：
@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    description = 'AI绘画（图像生成）服务，输入文本描述和图像分辨率，返回根据文本信息绘制的图片URL。'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': '详细描述了希望生成的图像具有什么内容，例如人物、环境、动作等细节描述，使用英文',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)


tools = ['my_image_gen', 'amap_weather']  # amap_weather是框架预置的工具
bot = Assistant(llm=llm_cfg,
                system_message=system,
                function_list=tools,
                files=[os.path.abspath('poem.pdf')])

messages = []
while True:
    query = input('user question: ')
    messages.append({'role': 'user', 'content': query})
    response = []
    for response in bot.run(messages=messages):
        print('bot response:', response)
    messages.extend(response)
