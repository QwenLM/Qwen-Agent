import os

from qwen_agent.agents import Assistant
from qwen_agent.utils.utils import save_text_to_file

llm_cfg = {
    'model': 'qwen-max',
    'model_server': 'dashscope',
    'generate_cfg': {
        'top_p': 0.8
    }
}

llm_cfg_vl = {
    'model': 'qwen-vl-plus',
    'model_server': 'dashscope',
    'generate_cfg': {
        'top_p': 0.8
    }
}

bot = Assistant(llm=llm_cfg,
                system_message='你扮演一个小学六年级的学生，你需要先理解图片内容，根据描述图片信息以后，' +
                '参考知识库中教你的写作技巧，发挥你的想象力，写一篇800字的记叙文',
                files=[os.path.abspath('writing_skill.pdf')])

bot_vl = Assistant(llm=llm_cfg_vl)

messages = [{
    'role':
    'user',
    'content': [{
        'text': '请详细描述这张图片的所有细节内容'
    }, {
        'image':
        'https://img01.sc115.com/uploads3/sc/vector/201809/51413-20180914205509.jpg'
    }]
}]

response = bot_vl.run(messages)
for x in response:
    print(x)
messages.extend(x)

messages.append({'role': 'user', 'content': '开始根据以上图片内容编写你的记叙文吧！'})
response = bot.run(messages)

for chunk in response:
    print(chunk[-1]['content'])

save_text_to_file('write_from_picture_output.md', chunk[-1]['content'])
