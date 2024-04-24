import copy
from typing import Iterator, List

from qwen_agent import Agent
from qwen_agent.llm.schema import CONTENT, ROLE, SYSTEM, Message

PROMPT_TEMPLATE_ZH = """
请充分理解以下参考资料内容，组织出满足用户提问的条理清晰的回复。
#参考资料：
{ref_doc}

"""

PROMPT_TEMPLATE_EN = """
Please fully understand the content of the following reference materials and organize a clear response that meets the user's questions.
# Reference materials:
{ref_doc}

"""

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}


class DocQA(Agent):

    def _run(self, messages: List[Message], knowledge: str = '', lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)
        system_prompt = PROMPT_TEMPLATE[lang].format(ref_doc=knowledge)
        if messages[0][ROLE] == SYSTEM:
            messages[0][CONTENT] += system_prompt
        else:
            messages.insert(0, Message(SYSTEM, system_prompt))

        return self._call_llm(messages=messages)
