import os

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import Message


def test_llm_oai():
    # settings
    llm_cfg = {
        'model': 'Qwen/Qwen1.5-14B-Chat',
        'model_server': 'https://api.together.xyz',
        'api_key': os.getenv('TOGETHER_API_KEY')
    }
    functions = [{
        'name': 'image_gen',
        'description': 'AI绘画（图像生成）服务，输入文本描述和图像分辨率，返回根据文本信息绘制的图片URL。',
        'parameters': {
            'type': 'object',
            'properties': {
                'prompt': {
                    'type': 'string',
                    'description': '详细描述了希望生成的图像具有什么内容，例如人物、环境、动作等细节描述，使用英文',
                },
            },
            'required': ['prompt'],
        }
    }]

    llm = get_chat_model(llm_cfg)
    messages = [{'role': 'user', 'content': 'hi'}]
    *_, last = llm.chat(messages, stream=True)
    assert isinstance(last[-1]['content'], str)
    messages.extend(last)

    messages.append(Message('user', 'draw a cute cat'))
    *_, last = llm.chat(messages, functions=functions, stream=True)
    assert isinstance(last[-1]['content'], str)
    assert last[-1].function_call.name == 'image_gen'
