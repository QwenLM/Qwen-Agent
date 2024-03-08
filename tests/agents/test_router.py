from qwen_agent.agents import Assistant, Router
from qwen_agent.llm.schema import ContentItem, Message


def test_router():
    llm_cfg = {'model': 'qwen-max'}
    llm_cfg_vl = {'model': 'qwen-vl-max'}
    tools = ['image_gen', 'amap_weather']

    # define a vl agent
    bot_vl = Assistant(llm=llm_cfg_vl)

    # define a tool agent
    bot_tool = Assistant(llm=llm_cfg, function_list=tools)

    # define a router (Simultaneously serving as a text agent)
    bot = Router(llm=llm_cfg,
                 agents={
                     'vl': {
                         'obj': bot_vl,
                         'desc': '多模态助手，可以理解图像内容。'
                     },
                     'tool': {
                         'obj': bot_tool,
                         'desc': '工具助手，可以使用天气查询工具和画图工具来解决问题'
                     }
                 })
    messages = [
        Message(
            'user',
            [
                ContentItem(text='描述图片'),
                ContentItem(
                    image=  # NOQA
                    'https://img01.sc115.com/uploads/sc/jpgs/1505/apic11540_sc115.com.jpg'
                )
            ])
    ]

    *_, last = bot.run(messages)
    assert isinstance(last[-1].content, str)

    messages = [Message('user', '海淀区天气')]

    *_, last = bot.run(messages)
    assert last[-3].function_call.name == 'amap_weather'
    assert last[-3].function_call.arguments == '{"location": "海淀区"}'
    assert last[-2].name == 'amap_weather'
    assert len(last[-1].content) > 0
