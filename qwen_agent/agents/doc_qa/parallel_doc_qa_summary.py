import copy
from typing import Iterator, List

from qwen_agent.agent import Agent
from qwen_agent.llm.schema import CONTENT, ROLE, SYSTEM, USER, ContentItem, Message
from qwen_agent.utils.utils import extract_text_from_message

PROMPT_TEMPLATE_ZH = """注意：你的回答必须严格遵循知识库内容，即使与事实不符。
如果知识库的大部分内容都与问题无关，只有少数几句话与问题直接相关，请重点关注这几句话，这种情况一定要回复。

# 知识库

{ref_doc}"""

PROMPT_TEMPLATE_EN = """Please respond solely based on the content of the provided Knowledge Base.
Note: Your answer must strictly adhere to the content of the provided Knowledge Base, even if it deviates from the facts.
If the materials mainly contains content irrelevant to the question, with only a few sentences directly related, please focus on these sentences and ensure a response.

# Knowledge Base

{ref_doc}"""

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}

PROMPT_END_TEMPLATE_ZH = """# 问题
{question}


# 回答规则
- 请基于知识库内容回答问题。注意：你的回答必须严格遵循知识库内容，即使与事实不符。
- 如果知识库的大部分内容都与问题无关，只有少数几句话与问题直接相关，请重点关注这几句话，这种情况一定要回复。

请根据回答规则，针对知识库内容回答问题，回答："""

PROMPT_END_TEMPLATE_EN = """# Question
{question}


# Answering Guidelines
- Please respond solely based on the content of the provided Knowledge Base.
- Note: Your answer must strictly adhere to the content of the provided Knowledge Base, even if it deviates from the facts.
- If the materials mainly contains content irrelevant to the question, with only a few sentences directly related, please focus on these sentences and ensure a response.

Please give your answer:"""

PROMPT_END_TEMPLATE = {
    'zh': PROMPT_END_TEMPLATE_ZH,
    'en': PROMPT_END_TEMPLATE_EN,
}


class ParallelDocQASummary(Agent):

    def _run(self, messages: List[Message], knowledge: str = '', lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)

        system_prompt = PROMPT_TEMPLATE[lang].format(ref_doc=knowledge)

        if messages[0][ROLE] == SYSTEM:
            if isinstance(messages[0][CONTENT], str):
                messages[0][CONTENT] += '\n\n' + system_prompt
            else:
                assert isinstance(messages[0][CONTENT], list)
                messages[0][CONTENT] += [ContentItem(text='\n\n' + system_prompt)]
        else:
            messages.insert(0, Message(SYSTEM, system_prompt))

        assert messages[-1][ROLE] == USER, messages
        user_question = extract_text_from_message(messages[-1], add_upload_info=False)
        messages[-1] = Message(USER, PROMPT_END_TEMPLATE[lang].format(question=user_question))

        return self._call_llm(messages=messages)
