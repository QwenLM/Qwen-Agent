from qwen_agent.agents.actions.base import Action

PROMPT_TEMPLATE_CN = """
你是一个写作助手，请依据参考资料，充分理解参考资料内容，组织出满足用户需求的条理清晰的回复。如果用户需求中没有指定回复语言，则回复语言必须与用户需求的语言保持一致。
#参考资料：
{ref_doc}

#用户需求：
{user_request}

"""

PROMPT_TEMPLATE_EN = """
You are a writing assistant. Please fully understand the content of the reference materials, and organize a clear response that meets the user requirements.
If the response language is not specified in the user requirements, the response language must be consistent with the language of the user requirements.

# References:
{ref_doc}

# User Requirements:
{user_request}

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

"""


class Simple(Action):
    def __init__(self, llm=None, stream=False):
        super().__init__(llm=llm, stream=stream)

    def run(self, ref_doc, user_request, messages=None, prompt_lan='CN'):
        history = ''
        query = user_request
        if isinstance(user_request, list):  # history
            history = self._get_history(user_request[:-1])
            query = user_request[-1][0]
        if history:
            if prompt_lan == 'CN':
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
        return self._run(prompt, messages=messages)
