import json
import urllib.parse

import json5

from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool

llm_cfg = {
    # If using Dashscope API
    'model': 'qwen-max',
    'model_server': 'dashscope',
    # If using self deployed OpenAI API model services
    # 'model': 'Qwen',
    # 'model_server': 'http://127.0.0.1:7905/v1',
    'generate_cfg': {
        'top_p': 0.8
    }
}
system = 'According to the user\'s request, you first draw a picture and then automatically run code to download the picture to image.jpg'


# add a customized tool named my_image_gen：
@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    description = 'AI painting (image generation) service, input text description, and return the image URL drawn based on text information.'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description':
        'Detailed description of the desired image content, in English',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)


tools = ['my_image_gen', 'code_interpreter'
         ]  # code_interpreter is a built-in tool in Qwen-Agent
bot = Assistant(llm=llm_cfg, system_message=system, function_list=tools)

messages = []
while True:
    query = input('user question: ')
    messages.append({'role': 'user', 'content': query})
    response = []
    for response in bot.run(messages=messages):
        print('bot response:', response)
    messages.extend(response)
