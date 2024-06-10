import json
import urllib.parse

import json5

from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool


class MyImageGen(BaseTool):
    name = 'my_image_gen'
    description = 'AI painting (image generation) service, input text description, and return the image URL drawn based on text information.'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': 'Detailed description of the desired image content, in English',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json.dumps({'image_url': f'https://image.pollinations.ai/prompt/{prompt}'}, ensure_ascii=False)


def init_agent_service():
    llm_cfg = {'model': 'qwen-max'}
    system = ('According to the user\'s request, you must draw a picture with my_image_gen tool')

    tools = [MyImageGen(), 'code_interpreter']  # code_interpreter is a built-in tool in Qwen-Agent
    bot = Assistant(llm=llm_cfg, system_message=system, function_list=tools)

    return bot


def test_custom_tool_object():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = [{'role': 'user', 'content': 'draw a dog'}]
    for response in bot.run(messages=messages):
        print('bot response:', response)

    assert len(response) == 3
    assert response[1]['role'] == 'function' and response[1]['name'] == 'my_image_gen'
