import os

from qwen_agent.agents import Assistant

system = '你扮演一个图文能力并存的助手。你还可以运行代码。你需要用知识库里的一首诗描述给你的图。'
llm_cfg = {
    'model': 'qwen-max',
    'model_server': 'dashscope',
    'generate_cfg': {
        'top_p': 0.8
    }
}
tools = ['image_gen', 'code_interpreter']
bot = Assistant(llm=llm_cfg,
                system_message=system,
                function_list=tools,
                files=[os.path.abspath('poem.pdf')])

messages = []
while True:
    query = input('user question: ')
    messages.append({
        'role':
        'user',
        'content': [{
            'text': query
        }, {
            'file': os.path.abspath('poem.pdf')
        }, {
            'image':
            'https://img01.sc115.com/uploads/sc/jpgs/1505/apic11540_sc115.com.jpg'
        }]
    })
    response = []
    for response in bot.run(messages=messages):
        print('bot response:', response)
    messages.extend(response)
