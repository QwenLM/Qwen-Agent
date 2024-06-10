from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import ContentItem, Message


def test_assistant_system_and_tool():
    llm_cfg = {'model': 'qwen-max'}
    system = '你扮演一个天气预报助手，你具有查询天气能力。'

    tools = ['image_gen', 'amap_weather']
    agent = Assistant(llm=llm_cfg, system_message=system, function_list=tools)

    messages = [Message('user', '海淀区天气')]

    *_, last = agent.run(messages)

    assert last[-3].function_call.name == 'amap_weather'
    assert last[-3].function_call.arguments == '{"location": "海淀区"}'
    assert last[-2].name == 'amap_weather'
    assert len(last[-1].content) > 0


def test_assistant_files():
    llm_cfg = {'model': 'qwen-max'}
    agent = Assistant(llm=llm_cfg)

    messages = [
        Message('user', [
            ContentItem(text='总结一个文章标题'),
            ContentItem(
                file='https://help.aliyun.com/zh/dashscope/developer-reference/api-details?disableWebsiteRedirect=true')
        ])
    ]

    *_, last = agent.run(messages)

    assert len(last[-1].content) > 0


def test_assistant_vl():
    llm_cfg = {'model': 'qwen-vl-max'}
    agent = Assistant(llm=llm_cfg)

    messages = [
        Message(
            'user',
            [
                ContentItem(text='用一句话描述图片'),
                ContentItem(image=  # NOQA
                            'https://img01.sc115.com/uploads/sc/jpgs/1505/apic11540_sc115.com.jpg')
            ])
    ]

    *_, last = agent.run(messages)

    assert len(last[-1].content) > 0
