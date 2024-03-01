"""A multi-agent cooperation example implemented by router and assistant"""
from qwen_agent.agents import Assistant, ReActChat, Router


def init_agent_service():
    # settings
    llm_cfg = {'model': 'qwen-max'}
    llm_cfg_vl = {'model': 'qwen-vl-max'}
    tools = ['image_gen', 'code_interpreter']

    # define a vl agent
    bot_vl = Assistant(llm=llm_cfg_vl)

    # define a tool agent
    bot_tool = ReActChat(llm=llm_cfg, function_list=tools)

    # define a router (Simultaneously serving as a text agent)
    bot = Router(llm=llm_cfg,
                 agents={
                     'vl': {
                         'obj': bot_vl,
                         'desc': '多模态助手，可以理解图像内容。'
                     },
                     'tool': {
                         'obj': bot_tool,
                         'desc': '工具助手，可以使用画图工具和运行代码来解决问题'
                     }
                 })
    return bot


def app():
    # define the agent
    bot = init_agent_service()

    # chat
    messages = []
    while True:
        query = input('user question: ')
        # image example: https://img01.sc115.com/uploads/sc/jpgs/1505/apic11540_sc115.com.jpg
        image = input('image url (press enter if no image): ')
        # file example: resource/poem.pdf
        file = input('file url (press enter if no file): ').strip()
        if not query:
            print('user question cannot be empty！')
            continue
        if not image and not file:
            messages.append({'role': 'user', 'content': query})
        else:
            messages.append({'role': 'user', 'content': [{'text': query}]})
            if image:
                messages[-1]['content'].append({'image': image})
            if file:
                messages[-1]['content'].append({'file': file})

        response = []
        for response in bot.run(messages):
            print('bot response:', response)
        messages.extend(response)


if __name__ == '__main__':
    app()
