from qwen_agent.actions.base import Action

PROMPT_TEMPLATE_ZH = """
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

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}


class RetrievalQA(Action):

    def _run(self, user_request, ref_doc, lang: str = 'en'):
        query = user_request
        prompt = PROMPT_TEMPLATE[lang].format(
            ref_doc=ref_doc,
            user_request=query,
        )
        return self._call_llm(prompt)
