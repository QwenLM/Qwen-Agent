from qwen_agent.actions.base import Action

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


class RetrievalQA(Action):

    def run(self, user_request, ref_doc, prompt_lan='CN'):
        history = ''
        query = user_request
        prompt = query
        if history:
            if prompt_lan == 'CN':  # testing
                prompt = PROMPT_TEMPLATE_WITH_HISTORY_CN.format(
                    ref_doc=ref_doc, history=history, user_request=query)
            elif prompt_lan == 'EN':
                prompt = PROMPT_TEMPLATE_WITH_HISTORY_EN.format(
                    ref_doc=ref_doc, history=history, user_request=query)
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

        return self._call_llm(prompt)
