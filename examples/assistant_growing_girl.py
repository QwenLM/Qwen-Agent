"""A girl's growth story novelist implemented by assistant"""
from qwen_agent.agents import Assistant


def create_agent():
    # settings
    llm_cfg = {'model': 'qwen-max'}
    tools = ['image_gen']
    bot = Assistant(llm=llm_cfg,
                    function_list=tools,
                    system_message='你扮演一个漫画家，根据我给你的女孩的不同阶段，使用工具画出每个阶段女孩的的图片，'
                    '并串成一个故事讲述出来。要求图片背景丰富')
    return bot


def main():
    # define the agent
    bot = create_agent()

    # chat
    messages = []
    while True:
        # query example: 请开始创作！
        query = input('user question: ')
        # file example: resource/growing_girl.pdf
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
