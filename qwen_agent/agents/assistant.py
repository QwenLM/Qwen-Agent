import copy
from typing import Iterator, List

from qwen_agent.llm.schema import CONTENT, ROLE, SYSTEM, Message
from qwen_agent.log import logger
from qwen_agent.utils.utils import format_knowledge_to_source_and_content

from .fncall_agent import FnCallAgent

KNOWLEDGE_SNIPPET_ZH = """## 来自 {source} 的内容：

```
{content}
```"""
KNOWLEDGE_TEMPLATE_ZH = """

# 知识库

{knowledge}"""

KNOWLEDGE_SNIPPET_EN = """## The content from {source}:

```
{content}
```"""
KNOWLEDGE_TEMPLATE_EN = """

# Knowledge Base

{knowledge}"""

KNOWLEDGE_SNIPPET = {'zh': KNOWLEDGE_SNIPPET_ZH, 'en': KNOWLEDGE_SNIPPET_EN}
KNOWLEDGE_TEMPLATE = {'zh': KNOWLEDGE_TEMPLATE_ZH, 'en': KNOWLEDGE_TEMPLATE_EN}


class Assistant(FnCallAgent):
    """This is a widely applicable agent integrated with RAG capabilities and function call ability."""

    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             max_ref_token: int = 4000,
             **kwargs) -> Iterator[List[Message]]:

        new_messages = self._prepend_knowledge_prompt(messages, lang,
                                                      max_ref_token)
        return super()._run(messages=new_messages,
                            lang=lang,
                            max_ref_token=max_ref_token,
                            **kwargs)

    def _prepend_knowledge_prompt(self,
                                  messages: List[Message],
                                  lang: str = 'en',
                                  max_ref_token: int = 4000) -> List[Message]:
        messages = copy.deepcopy(messages)
        # Retrieval knowledge from files
        *_, last = self.mem.run(messages=messages, max_ref_token=max_ref_token)
        knowledge = last[-1][CONTENT]

        logger.debug(
            f'Retrieved knowledge of type `{type(knowledge).__name__}`:\n{knowledge}'
        )
        if knowledge:
            knowledge = format_knowledge_to_source_and_content(knowledge)
            logger.debug(
                f'Formatted knowledge into type `{type(knowledge).__name__}`:\n{knowledge}'
            )
        else:
            knowledge = []
        snippets = []
        for k in knowledge:
            snippets.append(KNOWLEDGE_SNIPPET[lang].format(
                source=k['source'], content=k['content']))
        knowledge_prompt = ''
        if snippets:
            knowledge_prompt = KNOWLEDGE_TEMPLATE[lang].format(
                knowledge='\n\n'.join(snippets))

        if knowledge_prompt:
            if messages[0][ROLE] == SYSTEM:
                messages[0][CONTENT] += knowledge_prompt
            else:
                messages = [Message(role=SYSTEM, content=knowledge_prompt)
                            ] + messages
        return messages
