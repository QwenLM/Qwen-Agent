

class ChatApi:

    def __init__(self, agent):
        self.agent = agent

    def run_webui(self, chatbot_config=None, server_name='0.0.0.0', server_port=7860):
        from qwen_agent.gui import WebUI
        WebUI(
            self.agent,
            chatbot_config=chatbot_config,
        ).run(server_name=server_name, server_port=server_port)

    def run_apiserver(self, server_name='0.0.0.0', server_port=8080):
        from .api_server import start_apiserver
        start_apiserver(self, server_name, server_port)

    def add_type(self, item):
        if 'function_call' in item:
            item['type'] = 'function_call'
        elif item['role'] == 'function':
            item['type'] = 'function_call_output'
        elif 'chunk' in item:
            item['type'] = 'chunk'
        else:
            item['type'] = 'message'
        return item

    def gen_stream(self, response, add_full_msg=False):
        last = []
        last_msg = ""
        for rsp in response:
            now = rsp[-1]
            now_is_msg = 'function_call' not in now and now['role'] != 'function'
            is_new_line = len(last) != len(rsp)
            if is_new_line and last:
                res = self.add_type(last[-1])
                last_msg = ''
                if not add_full_msg or res['type'] != 'message':
                    yield res
            if now_is_msg:
                msg = now['content']
                assert msg.startswith(last_msg)
                stream_msg = msg[len(last_msg):]
                yield self.add_type({'role': now['role'], 'content': '', 'chunk': stream_msg})
                last_msg = msg
            last = rsp
            
        if last:
            res = self.add_type(last[-1])
            last_msg = ''
            if not add_full_msg or res['type'] != 'message':
                yield res

    def gen(self, response):
        last = None
        for rsp in response:
            if last is not None:
                if len(last) != len(rsp):
                    yield last[-1]
            last = rsp
        if last:
            yield last[-1]

    def chat(self, messages, stream=True):
        response = self.agent.run(messages)
        if stream:
            return self.gen_stream(response)
        else:
            return self.gen(response)
