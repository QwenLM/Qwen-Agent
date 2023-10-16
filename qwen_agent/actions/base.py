from qwen_agent.schema import Message
from qwen_agent.utils.util import count_tokens


class Action:
    def __init__(self, llm=None, stream=False):
        self.llm = llm
        self.stream = stream

    def _run(self, prompt=None, messages=None):
        return self.llm.chat(prompt, messages=messages, stream=self.stream)

    def _get_history(self, user_request, other_text, input_max_token=6000):
        history = ''
        other_len = count_tokens(other_text)
        print(other_len)
        valid_token_num = input_max_token - 100 - other_len
        for x in user_request[::-1]:
            now_history = '\n'
            now_history += Message('user', x[0]).to_str()
            now_history += '\n'
            now_history += Message('assistant', x[1]).to_str()
            now_token = count_tokens(now_history)
            if now_token <= valid_token_num:
                valid_token_num -= now_token
                history = now_history + history
            else:
                break
            break  # only adding one turn history
        return history
