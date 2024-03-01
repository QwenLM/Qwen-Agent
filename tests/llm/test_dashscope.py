from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import Message


def test_llm_dashscope_vl_mix_text():
    # settings
    llm_cfg = {'model': 'qwen-plus', 'model_server': 'dashscope'}
    llm_cfg_vl = {'model': 'qwen-vl-max', 'model_server': 'dashscope'}
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

    # chat with vl llm
    llm_vl = get_chat_model(llm_cfg_vl)
    messages = [{
        'role':
        'user',
        'content': [{
            'text': '框出太阳'
        }, {
            'image':
            'https://img01.sc115.com/uploads/sc/jpgs/1505/apic11540_sc115.com.jpg'
        }]
    }]
    *_, last = llm_vl.chat(messages, stream=True)
    assert isinstance(last[-1]['content'], list)
    messages.extend(last)

    # chat with text llm
    llm = get_chat_model(llm_cfg)
    messages.append(Message('user', 'draw a cute cat'))
    *_, last = llm.chat(messages, functions=functions, stream=True)
    assert isinstance(last[-1]['content'], str)
    assert last[-1].function_call.name == 'image_gen'
