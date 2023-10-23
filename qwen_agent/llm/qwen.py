import os
from http import HTTPStatus

import dashscope
import openai
from dashscope import Generation

from qwen_agent.llm.base import LLMBase


class Qwen(LLMBase):
    def __init__(self, model='qwen', api_key='', model_server=''):
        super().__init__(model=model, api_key=api_key)

        self.model_server = model_server
        self.source = ''
        self.gen = None

        if self.model_server.startswith('http'):
            openai.api_base = self.model_server
            openai.api_key = self.api_key
            self.source = 'local'
        elif self.model_server.startswith('dashscope'):
            dashscope.api_key = self.api_key or os.getenv('DASHSCOPE_API_KEY', default='')
            if not dashscope.api_key:
                print('There is no DASHSCOPE_API_KEY!')
            self.source = 'dashscope'

    def chat(self, query=None, stream=False, messages=None, stop=None):

        if self.source == 'dashscope':
            if dashscope.api_key:  # use dashscope interface
                print('Now using dashscope api')
                self.gen = Generation()
                return self._chat_dashscope(query, stream=stream, messages=messages, stop=stop)
            else:
                print('There is no DASHSCOPE_API_KEY!')
                return 'Failed! There is no DASHSCOPE_API_KEY!'
        else:  # use locally deployed qwen
            print('Now using locally deployed qwen')
            return super().chat(query, stream=stream, messages=messages, stop=stop)

    def _chat_stream(self, query, messages=None, stop=None):
        print('begin: stream in qwen')
        if messages:
            response = openai.ChatCompletion.create(model=self.model, messages=messages, stop=stop, stream=True)
        else:
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=[{
                                                        'role': 'user',
                                                        'content': query
                                                    }],
                                                    stop=stop,
                                                    stream=True)
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                print(chunk.choices[0].delta.content, end='', flush=True)
                yield chunk.choices[0].delta.content

    def _chat_no_stream(self, query, messages=None, stop=None):
        print('begin: no stream in qwen')
        if messages:
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=messages,
                                                    stop=stop,
                                                    stream=False)
        else:
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=[{
                                                        'role': 'user',
                                                        'content': query
                                                    }],
                                                    stop=stop,
                                                    stream=False)
        print(response.choices[0].message.content)
        return response.choices[0].message.content

    def _chat_dashscope(self, query, stream=False, messages=None, stop=None):
        if stream:
            return self._chat_dashscope_stream(query, messages, stop=stop)
        else:
            return self._chat_dashscope_no_stream(query, messages, stop=stop)

    def _chat_dashscope_stream(self, query, messages=None, stop=None):
        # print(query)
        if not stop:
            stop = []
        if messages:
            response = self.gen.call(
                self.model,
                messages=messages,
                result_format='message',  # set the result to be "message" format.
                stop_words=[{'stop_str': word, 'mode': 'exclude'} for word in stop],
                stream=True,
                top_p=0.8
            )
        else:
            response = self.gen.call(
                self.model,
                messages=[{
                            'role': 'user',
                            'content': query
                        }],
                result_format='message',  # set the result to be "message" format.
                stop_words=[{'stop_str': word, 'mode': 'exclude'} for word in stop],
                stream=True,
                top_p=0.8
            )
        last_len = 0
        delay_len = 5
        in_delay = 0
        text = ''
        for trunk in response:
            if trunk.status_code == HTTPStatus.OK:
                # print(trunk)
                text = trunk.output.choices[0].message.content
                if (len(text)-last_len) <= delay_len:  # less than delay_len
                    in_delay = 1
                    continue
                else:
                    in_delay = 0  # print
                    real_text = text[:-delay_len]  # delay print
                    now_rsp = real_text[last_len:]
                    yield now_rsp
                    last_len = len(real_text)
            else:
                err = 'Error code: %s, error message: %s' % (
                    trunk.code, trunk.message
                )
                if trunk.code == 'DataInspectionFailed':
                    err += '\n'
                    err += '错误码: 数据检查失败，错误信息: 输入数据可能包含不适当的内容。'
                print(err)
                text = ''
                yield f'{err}'
        if text and (in_delay == 1 or last_len != len(text)):
            yield text[last_len:]

    def _chat_dashscope_no_stream(self, query, messages=None, stop=None):
        print('begin: no stream in dashscope')
        if not stop:
            stop = []
        if messages:
            response = self.gen.call(
                self.model,
                messages=messages,
                result_format='message',  # set the result to be "message" format.
                stream=False,
                stop_words=[{'stop_str': word, 'mode': 'exclude'} for word in stop],
                top_p=0.8
            )
        else:
            response = self.gen.call(
                self.model,
                messages=[{
                            'role': 'user',
                            'content': query
                        }],
                result_format='message',  # set the result to be "message" format.
                stream=False,
                stop_words=[{'stop_str': word, 'mode': 'exclude'} for word in stop],
                top_p=0.8
            )
        # print(response)
        if response.status_code == HTTPStatus.OK:
            return response.output.choices[0].message.content
        else:
            err = 'Error code: %s, error message: %s' % (
                response.code, response.message
            )
            return err

    def qwen_chat_func(self, messages, functions=None):
        print('begin: no stream in qwen_chat_func')
        if not functions:
            functions = []
        if functions:
            response = openai.ChatCompletion.create(
                model=self.model, messages=messages, functions=functions
            )
        else:
            response = openai.ChatCompletion.create(model=self.model, messages=messages)
        return response.choices[0].message
