import copy
from typing import Iterator, List

from qwen_agent import Agent
from qwen_agent.llm.schema import CONTENT, Message

PROMPT_TEMPLATE_ZH = """你是一个写作助手，请依据参考资料，根据给定的前置文本续写合适的内容。
#参考资料：
{ref_doc}

#前置文本：
{user_request}

保证续写内容和前置文本保持连贯，请开始续写："""

PROMPT_TEMPLATE_EN = """You are a writing assistant, please follow the reference materials and continue to write appropriate content based on the given previous text.

# References:
{ref_doc}

# Previous text:
{user_request}

Please start writing directly, output only the continued text, do not repeat the previous text, do not say irrelevant words, and ensure that the continued content and the previous text remain consistent."""

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}


class ContinueWriting(Agent):

    def _run(self, messages: List[Message], knowledge: str = '', lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)
        messages[-1][CONTENT] = PROMPT_TEMPLATE[lang].format(
            ref_doc=knowledge,
            user_request=messages[-1][CONTENT],
        )
        return self._call_llm(messages)
