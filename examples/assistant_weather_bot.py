"""A weather forecast assistant implemented by assistant"""
from qwen_agent.agents import Assistant


def create_agent():
    llm_cfg = {'model': 'qwen-max'}
    system = (
        '你扮演一个天气预报助手，你具有查询天气和画图能力。'
        '你需要查询相应地区的天气，然后调用给你的画图工具绘制一张城市的图，并从给定的诗词文档中选一首相关的诗词来描述天气，不要说文档以外的诗词。')

    tools = ['image_gen', 'amap_weather']
    bot = Assistant(llm=llm_cfg, system_message=system, function_list=tools)

    return bot


def main():
    # define the agent
    bot = create_agent()

    # chat
    messages = []
    while True:
        # query example: 海淀区天气
        query = input('user question: ')
        # file example: resource/poem.pdf
        file = input('file url (press enter if no file): ')
        if not query:
            print('user question cannot be empty！')
            continue
        if not file:
            messages.append({'role': 'user', 'content': query})
        else:
            messages.append({
                'role': 'user',
                'content': [{
                    'text': query
                }, {
                    'file': file
                }]
            })

        response = []
        for response in bot.run(messages):
            print('bot response:', response)
        messages.extend(response)


if __name__ == '__main__':
    main()
