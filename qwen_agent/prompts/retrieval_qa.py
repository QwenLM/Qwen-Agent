from qwen_agent import Agent

PROMPT_TEMPLATE_ZH = """请充分理解以下参考资料内容，组织出满足用户提问的条理清晰的回复。
#参考资料：
{ref_doc}

请记住以上参考资料，明白了就请说“好的，我将依据参考资料回复之后的提问。”
"""

PROMPT_TEMPLATE_EN = """Please fully understand the content of the following reference materials and organize a clear response that meets the user's questions.
# Reference materials:
{ref_doc}

Please remember the above reference materials. If you understand, please say "Okay, I will reply to the questions based on the reference materials."
"""

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}

ANSWER_PROMPT_TEMPLATE_ZH = '好的，我将依据参考资料回复之后的提问。'

ANSWER_PROMPT_TEMPLATE_EN = 'Okay, I will reply to the questions based on the reference materials.'

ANSWER_PROMPT_TEMPLATE = {
    'zh': ANSWER_PROMPT_TEMPLATE_ZH,
    'en': ANSWER_PROMPT_TEMPLATE_EN,
}


class RetrievalQA(Agent):

    def _run(self, user_request, ref_doc, lang: str = 'en'):

        messages = [{
            'role': 'user',
            'content': PROMPT_TEMPLATE[lang].format(ref_doc=ref_doc),
        }, {
            'role': 'assistant',
            'content': ANSWER_PROMPT_TEMPLATE[lang],
        }, {
            'role': 'user',
            'content': user_request,
        }]

        return self._call_llm(messages=messages)
