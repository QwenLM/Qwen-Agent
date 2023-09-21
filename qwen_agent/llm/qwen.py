import openai

from qwen_agent.llm.base import LLMBase

openai.api_base = 'http://127.0.0.1:7905/v1'
openai.api_key = 'none'


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
