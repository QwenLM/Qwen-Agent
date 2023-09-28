from http import HTTPStatus

import openai


class LLMBase:
    def __init__(self, model='qwen', api_key='',):

        self.model = model
        self.memory = None
        self.gen = None
        self.api_key = api_key

    def chat(self, query, stream=False, messages=[]):
        if stream:
            return self.chat_stream(query, messages)
        else:
            return self.chat_no_stream(query, messages)

    def chat_dashscope(self, query, stream=False, messages=[], stop_words=[]):
        if stream:
            return self.chat_dashscope_stream(query, messages, stop_words=stop_words)
        else:
            return self.chat_dashscope_no_stream(query, messages, stop_words=stop_words)

    def chat_stream(self, query, messages=[]):
        print('begin: stream in base')
        if messages:
            response = openai.ChatCompletion.create(model=self.model, messages=messages, stream=True)
        else:
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=[{
                                                        'role': 'user',
                                                        'content': query
                                                    }],
                                                    stream=True)
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                print(chunk.choices[0].delta.content, end='', flush=True)
                yield chunk.choices[0].delta.content

    def chat_no_stream(self, query, messages=[]):
        print('begin: no stream in base')
        if messages:
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=messages,
                                                    stream=False)
        else:
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=[{
                                                        'role': 'user',
                                                        'content': query
                                                    }],
                                                    stream=False)
        print(response.choices[0].message.content)
        return response.choices[0].message.content

    def chat_dashscope_stream(self, query, messages=[], stop_words=[]):
        if messages:
            response = self.gen.call(
                self.model,
                messages=messages,
                result_format='message',  # set the result to be "message" format.
                stream=True,
            )
        else:
            response = self.gen.call(
                self.model,
                messages=[{
                            'role': 'user',
                            'content': query
                        }],
                result_format='message',  # set the result to be "message" format.
                stream=True,
            )
        last_len = 0
        for trunk in response:
            if trunk.status_code == HTTPStatus.OK:
                text = trunk.output.choices[0].message.content
                # print(text)
                if len(text) <= last_len:
                    continue
                now_rsp = text[last_len:]
                yield now_rsp
                last_len = len(text)
            else:
                err = 'Error code: %s, error message: %s' % (
                    trunk.code, trunk.message
                )
                if trunk.code == 'DataInspectionFailed':
                    err += '\n'
                    err += '错误码: 数据检查失败，错误信息: 输入数据可能包含不适当的内容。'
                print(err)
                yield f'{err}'

    def chat_dashscope_no_stream(self, query, messages=[], stop_words=[]):
        print('begin: no stream in base dashscope')
        if messages:
            response = self.gen.call(
                self.model,
                messages=messages,
                result_format='message',  # set the result to be "message" format.
                stream=False,
                stop_words=[{'stop_str': word, 'mode': 'include'} for word in stop_words],
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
                stop_words=[{'stop_str': word, 'mode': 'include'} for word in stop_words],
            )
        return response.output.choices[0].message.content
