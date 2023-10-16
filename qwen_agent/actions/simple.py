from qwen_agent.actions.base import Action
from qwen_agent.utils.util import count_tokens

PROMPT_TEMPLATE_CN = """
你是一个写作助手，请依据参考资料，组织出满足用户需求的条理清晰的回复。不要编造参考资料中不存在的内容。如果用户需求中没有指定回复语言，则回复语言必须与用户需求的语言保持一致。
#参考资料：
{ref_doc}

#用户需求：
{user_request}

#助手回复：
"""

PROMPT_TEMPLATE_EN = """
You are a writing assistant. Please fully understand the content of the reference materials, and organize a clear response that meets the user requirements.
If the response language is not specified in the user requirements, the response language must be consistent with the language of the user requirements.

# References:
{ref_doc}

# User Requirements:
{user_request}

# Assistant Response:
"""

PROMPT_TEMPLATE_WITH_HISTORY_CN = """
你是一个写作助手，请依据参考资料，充分理解参考资料内容，组织出满足用户需求的条理清晰的回复。
如果用户需求中没有指定回复语言，则回复语言必须与用户需求的语言保持一致。历史对话以```开始，以```结束，如果用户需求需要理解历史对话，你可以从中提取需要的信息，请注意你要解决的始终是用户需求，而不是历史对话中的问题。
#参考资料：
{ref_doc}

#历史对话
```
{history}
```

#用户需求：
{user_request}

#助手回复：
"""

PROMPT_TEMPLATE_WITH_HISTORY_EN = """
You are a writing assistant. Please fully understand the content of the reference materials, and organize a clear response that meets the user requirements.
If the response language is not specified in the user requirements, the response language must be consistent with the language of the user requirements.
The historical dialogue starts with ``` and ends with ```. If the user needs to understand the historical dialogue, you can extract the necessary information from it. Please note that you always need to solve the user requirements, not the problems in the historical dialogue.

# References:
{ref_doc}

# Historical Dialogue
```
{history}
```

# User Requirements:
{user_request}

# Assistant Response:
"""

PROMPT_TEMPLATE_FIRST_MESSAGE_CONCAT_REF = """
给定下列参考资料，请充分理解参考资料内容，组织出满足用户提问的条理清晰的回复。不要编造参考资料中不存在的信息。
#参考资料：
{ref_doc}

请记住以上信息。
"""


class Simple(Action):
    def __init__(self, llm=None, stream=False):
        super().__init__(llm=llm, stream=stream)

    def run(self, ref_doc, user_request, messages=None, prompt_lan='CN', input_max_token=6000):
        use_message = False
        if use_message:
            # debug
            return self.run_in_message(ref_doc, user_request, messages, prompt_lan, input_max_token)
        else:
            return self.run_in_one_turn_prompt(ref_doc, user_request, messages, prompt_lan, input_max_token)

    def run_in_one_turn_prompt(self, ref_doc, user_request, messages=None, prompt_lan='CN', input_max_token=6000):
        history = ''
        query = user_request
        if isinstance(user_request, list):  # history
            # Todo: consider history
            # history = self._get_history(user_request[:-1], ref_doc + user_request[-1][0], input_max_token)
            query = user_request[-1][0]
        prompt = query
        if history:
            if prompt_lan == 'CN':  # testing
                prompt = PROMPT_TEMPLATE_WITH_HISTORY_CN.format(
                    ref_doc=ref_doc,
                    history=history,
                    user_request=query
                )
            elif prompt_lan == 'EN':
                prompt = PROMPT_TEMPLATE_WITH_HISTORY_EN.format(
                    ref_doc=ref_doc,
                    history=history,
                    user_request=query
                )
        else:
            if prompt_lan == 'CN':
                prompt = PROMPT_TEMPLATE_CN.format(
                    ref_doc=ref_doc,
                    user_request=query,
                )
            elif prompt_lan == 'EN':
                prompt = PROMPT_TEMPLATE_EN.format(
                    ref_doc=ref_doc,
                    user_request=query,
                )

        # with open('long_prompt.txt', 'w') as f:
        #     f.write(prompt)

        return self._run(prompt, messages=messages)

    def run_in_message(self, ref_doc, user_request, messages=None, prompt_lan='CN', input_max_token=6000):
        if not messages:
            messages = [{
                'role': 'user',
                'content': PROMPT_TEMPLATE_FIRST_MESSAGE_CONCAT_REF.format(ref_doc=ref_doc),
            }, {
                'role': 'assistant',
                'content': '好的，我已经记住以上信息。有什么我能帮你回答的问题吗？',
            }]
            if isinstance(user_request, list):  # history
                history = self.get_history(user_request[:-1], ref_doc + user_request[-1][0], input_max_token)
                query = user_request[-1][0]
                messages += history
                messages.append({
                    'role': 'user',
                    'content': '先查看前面的参考资料, ' + query
                })
            else:
                messages.append({
                    'role': 'user',
                    'content': '先查看前面的参考资料, ' + user_request
                })
        with open('long_prompt.txt', 'w') as f:
            f.write(str(messages))

        return self._run(messages=messages)

    def get_history(self, user_request, other_text, input_max_token=6000):
        history = []
        other_len = count_tokens(other_text)
        print(other_len)
        valid_token_num = input_max_token - 100 - other_len
        for x in user_request[::-1]:
            now_history = [
                {
                    'role': 'user',
                    'content': x[0],
                }, {
                    'role': 'assistant',
                    'content': x[1],
                }
            ]

            now_token = count_tokens(x[0] + x[1])
            if now_token <= valid_token_num:
                valid_token_num -= now_token
                history = now_history + history
            else:
                break
            break  # only adding one turn history
        return history
