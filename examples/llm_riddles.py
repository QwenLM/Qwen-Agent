"""Customize an agent to implement llm riddles game"""
from typing import Dict, Iterator, List, Optional, Union

import json5

from qwen_agent import Agent
from qwen_agent.agents import Assistant
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import Message


class LLMRiddles(Agent):
    """Customize an agent for game: Surrounded by LLM """

    def __init__(self, llm: Optional[Union[Dict, BaseChatModel]] = None):
        super().__init__(llm=llm)

        # Nest one assistant for create questions
        self.examiner_agent = Assistant(llm=self.llm,
                                        system_message=('请你创造十个比较离谱或小众的短语，长度在10个汉字以内。例如“1+1=3”、“主莫朗玛峰”等反人类直觉的短语，'
                                                        '尽量类型丰富一些，包含数学、文学、地理、生物等领域。返回格式为字符串列表，不要返回其余任何内容。'))

        # Initialize the questions
        *_, last = self.examiner_agent.run([Message('user', '开始')])
        self.topics = json5.loads(last[-1].content)

    def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        return self._call_llm(messages=messages)


def test():
    # Define a writer agent
    bot = LLMRiddles(llm={'model': 'qwen-max'})

    # Gaming
    for topic in bot.topics:
        print(f'请你构造一个问题使模型的回答是一字不差的“{topic}”（不需要引号）。')

        messages = []
        query = f'请直接输出“{topic}”（不需要引号），不要说其他内容'

        messages.append(Message('user', query))

        response = []
        for response in bot.run(messages=messages):
            print('bot response:', response)
        if response and response[-1]['content'] == topic:
            print('You win!')


def app_tui():
    # Define a writer agent
    bot = LLMRiddles(llm={'model': 'qwen-max'})

    # Gaming
    for topic in bot.topics:
        print(f'请你构造一个问题使模型的回答是一字不差的“{topic}”（不需要引号）。')

        messages = []
        while True:
            query = input('user question(input EXIT for next topic): ')

            if query == 'EXIT':
                break
            messages.append(Message('user', query))
            response = []
            for response in bot.run(messages=messages):
                print('bot response:', response)
            if response and response[-1]['content'] == topic:
                print('You win!')
                break
            messages.extend(response)


if __name__ == '__main__':
    # test()
    app_tui()
