from qwen_agent.agents.schema import Message
from qwen_agent.llm.qwen import qwen_chat, qwen_chat_no_stream


class Action:
    def __init__(self, llm=None, stream=False):
        self.llm = llm
        self.stream = stream

    def _run(self, prompt, messages=None):
        if self.llm:
            return self.llm.chat(prompt, messages=messages, stream=self.stream)
        elif self.stream:
            return qwen_chat(prompt)
        else:
            return qwen_chat_no_stream(prompt)

    def _get_history(self, user_request):
        history = ''
        for x in user_request:
            history += Message('user', x[0]).to_str()
            history += '\n'
            history += Message('assistant', x[0]).to_str()
            history += '\n'
        return history
