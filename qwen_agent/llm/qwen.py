import os

import dashscope
import openai
from dashscope import Generation

from qwen_agent.llm.base import LLMBase


class Qwen(LLMBase):
    def __init__(self, model='qwen', api_key='', model_server=''):
        super().__init__(model=model, api_key=api_key)

        self.model_server = model_server
        self.source = ''

        if self.model_server.startswith('http'):
            openai.api_base = self.model_server
            openai.api_key = 'none'
            self.source = 'local'
        elif self.model_server.startswith('dashscope'):
            dashscope.api_key = self.api_key or os.getenv('DASHSCOPE_API_KEY', default='')
            if not dashscope.api_key:
                print('There is no DASHSCOPE_API_KEY!')
            self.source = 'dashscope'

    def chat(self, query, stream=False, messages=[], stop_words=[]):

        if self.source == 'dashscope':
            if dashscope.api_key:  # use dashscope interface
                print('Now using dashscope api')
                self.gen = Generation()
                return super().chat_dashscope(query, stream=stream, messages=messages, stop_words=stop_words)
            else:
                print('There is no DASHSCOPE_API_KEY!')
                return 'Failed! There is no DASHSCOPE_API_KEY!'
        else:  # use locally deployed qwen
            print('Now using locally deployed qwen')
            return super().chat(query, stream=stream, messages=messages)


"""
The following functions only support local Qwen services by default
"""


def qwen_chat(query, stream=True):
    if stream:
        print('begin: stream')
        for chunk in openai.ChatCompletion.create(model='Qwen',
                                                  messages=[{
                                                      'role': 'user',
                                                      'content': query
                                                  }],
                                                  stream=True):
            if hasattr(chunk.choices[0].delta, 'content'):
                # print(chunk.choices[0].delta.content, end='', flush=True)
                yield chunk.choices[0].delta.content


def qwen_chat_no_stream(query, messages=[], stream=False):
    print('begin: no stream')
    if messages:
        response = openai.ChatCompletion.create(model='Qwen',
                                                messages=messages,
                                                stream=False)
    else:
        response = openai.ChatCompletion.create(model='Qwen',
                                                messages=[{
                                                    'role': 'user',
                                                    'content': query
                                                }],
                                                stream=False)
    return response.choices[0].message.content


def qwen_chat_func(messages, functions=None):
    if functions:
        response = openai.ChatCompletion.create(
            model='Qwen', messages=messages, functions=functions
        )
    else:
        response = openai.ChatCompletion.create(model='Qwen', messages=messages)
    return response.choices[0].message


def qwen_chat_func_dashscope(messages, functions=None):
    pass
