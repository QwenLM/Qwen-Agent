from qwen_agent.agents import Assistant, Router
from qwen_agent.llm.schema import ContentItem, Message


def test_router():
    llm_cfg = {'model': 'qwen-max'}
    llm_cfg_vl = {'model': 'qwen-vl-max'}
    tools = ['amap_weather']

    # Define a vl agent
    bot_vl = Assistant(llm=llm_cfg_vl, name='多模态助手', description='可以理解图像内容。')

    # Define a tool agent
    bot_tool = Assistant(
        llm=llm_cfg,
        name='天气预报助手',
        description='可以查询天气',
        function_list=tools,
    )

    # define a router (Simultaneously serving as a text agent)
    bot = Router(llm=llm_cfg, agents=[bot_vl, bot_tool])
    messages = [
        Message('user', [
            ContentItem(text='描述图片'),
            ContentItem(image='https://img01.sc115.com/uploads/sc/jpgs/1505/apic11540_sc115.com.jpg'),
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
