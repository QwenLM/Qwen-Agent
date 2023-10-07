from qwen_agent.schema import Message


class Action:
    def __init__(self, llm=None, stream=False):
        self.llm = llm
        self.stream = stream

    def _run(self, prompt, messages=None):
        return self.llm.chat(prompt, messages=messages, stream=self.stream)

    def _get_history(self, user_request):
        history = ''
        for x in user_request:
            history += Message('user', x[0]).to_str()
            history += '\n'
            history += Message('assistant', x[0]).to_str()
            history += '\n'
        return history
