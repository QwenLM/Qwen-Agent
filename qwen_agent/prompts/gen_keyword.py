import copy
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm import get_chat_model
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import CONTENT, DEFAULT_SYSTEM_MESSAGE, Message
from qwen_agent.tools import BaseTool

PROMPT_TEMPLATE_ZH = """请提取问题中的关键词，需要中英文均有，可以适量补充不在问题中但相关的关键词。关键词尽量切分为动词/名词/形容词等类型，不要长词组。关键词以JSON的格式给出，比如{{"keywords_zh": ["关键词1", "关键词2"], "keywords_en": ["keyword 1", "keyword 2"]}}

Question: 这篇文章的作者是谁？
Keywords: {{"keywords_zh": ["作者"], "keywords_en": ["author"]}}
Observation: ...

Question: 解释下图一
Keywords: {{"keywords_zh": ["图一", "图 1"], "keywords_en": ["Figure 1"]}}
Observation: ...

Question: 核心公式
Keywords: {{"keywords_zh": ["核心公式", "公式"], "keywords_en": ["core formula", "formula", "equation"]}}
Observation: ...

Question: {user_request}
Keywords:
"""

PROMPT_TEMPLATE_EN = """Please extract keywords from the question, both in Chinese and English, and supplement them appropriately with relevant keywords that are not in the question. Try to divide keywords into verb/noun/adjective types and avoid long phrases.
Keywords are provided in JSON format, such as {{"keywords_zh": ["关键词1", "关键词2"], "keywords_en": ["keyword 1", "keyword 2"]}}

Question: Who are the authors of this article?
Keywords: {{"keywords_zh": ["作者"], "keywords_en": ["author"]}}
Observation: ...

Question: Explain Figure 1
Keywords: {{"keywords_zh": ["图一", "图 1"], "keywords_en": ["Figure 1"]}}
Observation: ...

Question: core formula
Keywords: {{"keywords_zh": ["核心公式", "公式"], "keywords_en": ["core formula", "formula", "equation"]}}
Observation: ...

Question: {user_request}
Keywords:
"""

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}


class GenKeyword(Agent):

    # TODO: Adding a stop word is not conveient! We should fix this later.
    def __init__(self,
                 function_list: Optional[List[Union[str, Dict,
                                                    BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 **kwargs):
        if llm is not None:  # TODO: Why this happens?
            llm = copy.deepcopy(llm)
            if isinstance(llm, dict):
                llm = get_chat_model(llm)
            stop = llm.generate_cfg.get('stop', [])
            key_stop = ['Observation:', 'Observation:\n']
            llm.generate_cfg['stop'] = stop + [
                x for x in key_stop if x not in stop
            ]
        super().__init__(function_list, llm, system_message, **kwargs)

    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)
        messages[-1][CONTENT] = PROMPT_TEMPLATE[lang].format(
            user_request=messages[-1][CONTENT])
        return self._call_llm(messages)
