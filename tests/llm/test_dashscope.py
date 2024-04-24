import pytest

from qwen_agent.llm import ModelServiceError, get_chat_model
from qwen_agent.llm.schema import Message

functions = [{
    'name': 'image_gen',
    'name_for_human': 'AI绘画',
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
    },
    'args_format': '参数为json格式'
}]


@pytest.mark.parametrize('functions', [None, functions])
@pytest.mark.parametrize('stream', [True, False])
@pytest.mark.parametrize('delta_stream', [True, False])
def test_vl_mix_text(functions, stream, delta_stream):
    if delta_stream:
        pytest.skip('Skipping this combination')

    # setting
    llm_cfg_vl = {'model': 'qwen-vl-max', 'model_server': 'dashscope'}

    # Chat with vl llm
    llm_vl = get_chat_model(llm_cfg_vl)
    messages = [{
        'role': 'user',
        'content': [{
            'text': '框出太阳'
        }, {
            'image': 'https://img01.sc115.com/uploads/sc/jpgs/1505/apic11540_sc115.com.jpg'
        }]
    }]
    response = llm_vl.chat(messages=messages, functions=None, stream=stream, delta_stream=delta_stream)
    if stream:
        response = list(response)[-1]

    assert isinstance(response[-1]['content'], str)


@pytest.mark.parametrize('functions', [None, functions])
@pytest.mark.parametrize('stream', [True, False])
@pytest.mark.parametrize('delta_stream', [False])
def test_llm_dashscope(functions, stream, delta_stream):
    if not stream and delta_stream:
        pytest.skip('Skipping this combination')

    if delta_stream and functions:
        pytest.skip('Skipping this combination')

    # setting
    llm_cfg = {'model': 'qwen-max', 'model_server': 'dashscope'}

    # Chat with text llm
    llm = get_chat_model(llm_cfg)
    messages = [Message('user', 'draw a cute cat')]
    response = llm.chat(messages=messages, functions=functions, stream=stream, delta_stream=delta_stream)
    if stream:
        response = list(response)[-1]
    assert isinstance(response[-1]['content'], str)
    if functions:
        assert response[-1].function_call.name == 'image_gen'
    else:
        assert response[-1].function_call is None


@pytest.mark.parametrize('stream', [True, False])
@pytest.mark.parametrize('delta_stream', [True, False])
def test_llm_retry_failure(stream, delta_stream):
    llm_cfg = {'model': 'qwen-turbo', 'api_key': 'invalid', 'generate_cfg': {'max_retries': 3}}

    llm = get_chat_model(llm_cfg)
    assert llm.max_retries == 3

    messages = [Message('user', 'hello')]
    with pytest.raises(ModelServiceError):
        response = llm.chat(messages=messages, stream=stream, delta_stream=delta_stream)
        if stream:
            list(response)
