import json
import urllib.parse

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import ContentItem


def image_gen(prompt: str) -> str:
    prompt = urllib.parse.quote(prompt)
    image_url = f'https://image.pollinations.ai/prompt/{prompt}'
    return image_url


def test():
    # Config for the model
    llm_cfg_oai = {
        # Using Qwen2-VL deployed at any openai-compatible service such as vLLM:
        'model_type': 'qwenvl_oai',
        'model': 'Qwen/Qwen2-VL-72B-Instruct',
        'model_server': 'http://localhost:8000/v1',  # api_base
        'api_key': 'EMPTY',
    }
    llm = get_chat_model(llm_cfg_oai)

    # Initial conversation
    messages = [{
        'role':
            'user',
        'content': [{
            'image': 'https://dashscope.oss-cn-beijing.aliyuncs.com/images/dog_and_girl.jpeg'
        }, {
            'text': '图片中的内容是什么？请画一张内容相同，风格类似的图片。'
        }]
    }]

    functions = [
        {
            'name': 'image_gen',
            'description': 'AI绘画（图像生成）服务，输入文本描述，返回根据文本信息绘制的图片URL。',
            'parameters': {
                'name': 'prompt',
                'type': 'string',
                'description': '详细描述了希望生成的图像具有什么内容，例如人物、环境、动作等细节描述，使用英文',
                'required': True
            }
        },
    ]

    print('# Assistant Response 1:')
    responses = []
    for responses in llm.chat(messages=messages, functions=functions, stream=True):
        print(responses)
    messages.extend(responses)

    for rsp in responses:
        if rsp.get('function_call', None):
            func_name = rsp['function_call']['name']
            if func_name == 'image_gen':
                func_args = json.loads(rsp['function_call']['arguments'])
                image_url = image_gen(func_args['prompt'])
                print('# Function Response:')
                func_rsp = {
                    'role': 'function',
                    'name': func_name,
                    'content': [ContentItem(image=image_url),
                                ContentItem(text=f'（ 这张图片的URL是 {image_url} ）')],
                }
                messages.append(func_rsp)
                print(func_rsp)
            else:
                raise NotImplementedError

    print('# Assistant Response 2:')
    responses = []
    for responses in llm.chat(messages=messages, functions=functions, stream=True):
        print(responses)
    messages.extend(responses)


if __name__ == '__main__':
    test()
