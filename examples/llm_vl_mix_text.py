"""An example of calling text and vl llm interfaces alternately"""
from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import ContentItem, Message


def test():
    llm_cfg = {'model': 'qwen-max', 'model_server': 'dashscope'}
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

    # Chat with vl llm
    llm_vl = get_chat_model(llm_cfg_vl)
    messages = [{
        'role':
        'user',
        'content': [{
            'text': '框出太阳并描述'
        }, {
            'image':
            'https://img01.sc115.com/uploads/sc/jpgs/1505/apic11540_sc115.com.jpg'
        }]
    }]
    response = llm_vl.chat(messages, stream=True)
    for x in response:
        print(x)
    messages.extend(x)

    messages.append(Message('user', [ContentItem(text='描述更详细一点')]))
    response = llm_vl.chat(messages, stream=True)
    for x in response:
        print(x)
    messages.extend(x)

    # Chat with text llm
    llm = get_chat_model(llm_cfg)
    messages.append({'role': 'user', 'content': '你是？'})
    response = llm.chat(messages, stream=True)
    for x in response:
        print(x)
    messages.extend(x)

    messages.append({'role': 'user', 'content': '画个可爱小猫'})
    response = llm.chat(messages, functions=functions, stream=True)
    for x in response:
        print(x)
    messages.extend(x)

    # Simulation function call results
    messages.append({
        'role':
        'function',
        'name':
        'image_gen',
        'content':
        '![fig-001](https://seopic.699pic.com/photo/60098/4947.jpg_wh1200.jpg)'
    })
    response = llm.chat(messages, functions=functions, stream=True)
    for x in response:
        print(x)
    messages.extend(x)

    # Chat with vl llm
    messages.append({
        'role':
        'user',
        'content': [{
            'text': '可以描述下这张图片吗？'
        }, {
            'image':
            'https://seopic.699pic.com/photo/60098/4947.jpg_wh1200.jpg'
        }]
    })
    response = llm_vl.chat(messages, stream=True)
    for x in response:
        print(x)
    messages.extend(x)


if __name__ == '__main__':
    test()
