import os

import pytest

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import Message

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


@pytest.mark.parametrize('functions', [None, functions])
@pytest.mark.parametrize('stream', [True, False])
@pytest.mark.parametrize('delta_stream', [True, False])
def test_llm_oai(functions, stream, delta_stream):
    if not stream and delta_stream:
        pytest.skip('Skipping this combination')

    if delta_stream and functions:
        pytest.skip('Skipping this combination')

    # settings
    llm_cfg = {
        'model': os.getenv('TEST_MODEL', 'Qwen/Qwen1.5-14B-Chat'),
        'model_server': os.getenv('TEST_MODEL_SERVER', 'https://api.together.xyz'),
        'api_key': os.getenv('TEST_MODEL_SERVER_API_KEY', 'none')
    }

    llm = get_chat_model(llm_cfg)
    assert llm.max_retries == 0

    messages = [Message('user', 'draw a cute cat')]
    response = llm.chat(messages=messages, functions=functions, stream=stream, delta_stream=delta_stream)
    if stream:
        response = list(response)[-1]

    assert isinstance(response[-1]['content'], str)
    if functions:
        assert response[-1].function_call.name == 'image_gen'
    else:
        assert response[-1].function_call is None
