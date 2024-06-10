"""Customize an agent to implement visual storytelling"""
import copy
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import ContentItem, Message
from qwen_agent.tools import BaseTool


class VisualStorytelling(Agent):
    """Customize an agent for writing story from pictures"""

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None):
        super().__init__(llm=llm)

        # Nest one vl assistant for image understanding
        self.image_agent = Assistant(llm={'model': 'qwen-vl-max'})

        # Nest one assistant for article writing
        self.writing_agent = Assistant(llm=self.llm,
                                       function_list=function_list,
                                       system_message='你扮演一个想象力丰富的学生，你需要先理解图片内容，根据描述图片信息以后，' +
                                       '参考知识库中教你的写作技巧，发挥你的想象力，写一篇800字的记叙文',
                                       files=['https://www.jianshu.com/p/cdf82ff33ef8'])

    def _run(self, messages: List[Message], lang: str = 'zh', **kwargs) -> Iterator[List[Message]]:
        """Define the workflow"""

        assert isinstance(messages[-1]['content'], list)
        assert any([item.image for item in messages[-1]['content']]), 'This agent requires input of images'

        # Image understanding
        new_messages = copy.deepcopy(messages)
        new_messages[-1]['content'].append(ContentItem(text='请详细描述这张图片的所有细节内容'))
        response = []
        for rsp in self.image_agent.run(new_messages):
            yield response + rsp
        response.extend(rsp)
        new_messages.extend(rsp)

        # Writing article
        new_messages.append(Message('user', '开始根据以上图片内容编写你的记叙文吧！'))
        for rsp in self.writing_agent.run(new_messages, lang=lang, **kwargs):
            yield response + rsp


def test(query: Optional[str] = '看图说话',
         image: str = 'https://img01.sc115.com/uploads3/sc/vector/201809/51413-20180914205509.jpg'):
    # define a writer agent
    bot = VisualStorytelling(llm={'model': 'qwen-max'})

    # Chat
    messages = [Message('user', [ContentItem(image=image)])]
    if query:
        messages[-1]['content'].append(ContentItem(text=query))

    for response in bot.run(messages):
        print('bot response:', response)


def app_tui():
    # Define a writer agent
    bot = VisualStorytelling(llm={'model': 'qwen-max'})

    # Chat
    messages = []
    while True:
        query = input('user question: ')
        # image example: https://img01.sc115.com/uploads3/sc/vector/201809/51413-20180914205509.jpg
        image = input('image url: ').strip()

        if not image:
            print('image cannot be empty！')
            continue
        messages.append(Message('user', [ContentItem(image=image)]))
        if query:
            messages[-1]['content'].append(ContentItem(text=query))

        response = []
        for response in bot.run(messages):
            print('bot response:', response)
        messages.extend(response)


def app_gui():
    bot = VisualStorytelling(llm={'model': 'qwen-max'})
    WebUI(bot).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
