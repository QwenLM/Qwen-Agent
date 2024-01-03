from qwen_agent import Agent

PROMPT_TEMPLATE_ZH = """请提取问题中的关键词，需要中英文均有，可以适量补充不在问题中但相关的关键词。关键词尽量切分为动词/名词/形容词等类型，不要长词组。关键词以JSON的格式给出，比如{{"keywords_zh": ["关键词1", "关键词2"], "keywords_en": ["keyword 1", "keyword 2"]}}

Question:这篇文章的作者是谁？
Keywords:{{"keywords_zh": ["作者"], "keywords_en": ["author"]}}

Question:解释下图一
Keywords:{{"keywords_zh": ["图一", "图 1"], "keywords_en": ["Figure 1"]}}

Question:核心公式
Keywords:{{"keywords_zh": ["核心公式", "公式"], "keywords_en": ["core formula", "formula", "equation"]}}

Question:{user_request}
Keywords:
"""

PROMPT_TEMPLATE_EN = """Please extract keywords from the question, both in Chinese and English, and supplement them appropriately with relevant keywords that are not in the question. Try to divide keywords into verb/noun/adjective types and avoid long phrases.
Keywords are provided in JSON format, such as {{"keywords_zh": ["关键词1", "关键词2"], "keywords_en": ["keyword 1", "keyword 2"]}}

Question: Who are the authors of this article?
Keywords:{{"keywords_zh": ["作者"], "keywords_en": ["author"]}}

Question: Explain Figure 1
Keywords:{{"keywords_zh": ["图一", "图 1"], "keywords_en": ["Figure 1"]}}

Question: core formula
Keywords:{{"keywords_zh": ["核心公式", "公式"], "keywords_en": ["core formula", "formula", "equation"]}}

Question:{user_request}
Keywords:
"""

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}


class GenKeyword(Agent):

    def _run(self, user_request, lang: str = 'en'):
        prompt = PROMPT_TEMPLATE[lang].format(user_request=user_request, )
        return self._call_llm(prompt)
