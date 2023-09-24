import json
import os

import openai

from qwen_agent.configs import config_browserqwen
from qwen_agent.llm.base import LLMBase

with open(os.path.join(config_browserqwen.work_space_root, 'config_openai.json')) as file:
    openai_cfg = json.load(file)

openai.api_base = openai_cfg['openai_api_base']
openai.api_key = openai_cfg['openai_api_key']


class Qwen(LLMBase):
    def __init__(self, model='Qwen-7B-Chat'):
        super().__init__(model=model)


def qwen_chat(query, stream=True):
    if stream:
        # 使用流式回复的请求
        print('begin: stream')
        for chunk in openai.ChatCompletion.create(model='Qwen-7B-Chat',
                                                  messages=[{
                                                      'role': 'user',
                                                      'content': query
                                                  }],
                                                  stream=True):
            if hasattr(chunk.choices[0].delta, 'content'):
                # print(chunk.choices[0].delta.content, end='', flush=True)
                yield chunk.choices[0].delta.content


def qwen_chat_no_stream(query, stream=False, stop_words=[]):
    print('begin: no stream')

    response = openai.ChatCompletion.create(model='Qwen-7B-Chat',
                                            messages=[{
                                                'role': 'user',
                                                'content': query
                                            }],
                                            stream=False,
                                            stop_words=stop_words)
    return response.choices[0].message.content


def qwen_chat_func(messages, functions=None):
    # print(messages)
    if functions:
        response = openai.ChatCompletion.create(
            model='Qwen', messages=messages, functions=functions
        )
    else:
        response = openai.ChatCompletion.create(model='Qwen', messages=messages)
    # print(response)
    # print(response.choices[0].message.content)
    return response.choices[0].message
