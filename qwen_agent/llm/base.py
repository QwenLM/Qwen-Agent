import openai


class LLMBase:
    def __init__(self, model='Qwen-7B-Chat'):

        self.model = model
        self.memory = None

    def chat(self, query, stream=False, messages=[]):
        if stream:
            # 使用流式回复的请求
            return self.chat_stream(query, messages)
        else:
            return self.chat_no_stream(query, messages)

    def chat_stream(self, query, messages=[]):
        # 使用流式回复的请求
        print('begin: stream in base')
        if messages:
            for chunk in openai.ChatCompletion.create(model=self.model, messages=messages, stream=True):
                if hasattr(chunk.choices[0].delta, 'content'):
                    print(chunk.choices[0].delta.content, end='', flush=True)
                    yield chunk.choices[0].delta.content
        else:
            for chunk in openai.ChatCompletion.create(model=self.model, messages=[{
                                                        'role': 'user',
                                                        'content': query
                                                    }], stream=True):
                if hasattr(chunk.choices[0].delta, 'content'):
                    print(chunk.choices[0].delta.content, end='', flush=True)
                    yield chunk.choices[0].delta.content

    def chat_no_stream(self, query, messages=[]):
        print('begin: no stream in base')
        if messages:
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=messages,
                                                    stream=False)
            print(response.choices[0].message.content)
            return response.choices[0].message.content
        else:
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=[{
                                                        'role': 'user',
                                                        'content': query
                                                    }],
                                                    stream=False)
            print(response.choices[0].message.content)
            return response.choices[0].message.content
