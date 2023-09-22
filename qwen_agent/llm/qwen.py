import json
from pathlib import Path

import openai

from qwen_agent.llm.base import LLMBase

with open(Path(__file__).resolve().parent.parent / 'configs/config_openai.json') as file:
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
