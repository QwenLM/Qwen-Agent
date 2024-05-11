from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.agents.assistant import Assistant
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import CONTENT, DEFAULT_SYSTEM_MESSAGE, Message
from qwen_agent.prompts import DocQA
from qwen_agent.tools import BaseTool

DEFAULT_NAME = 'Basic DocQA'
DEFAULT_DESC = '可以根据问题，检索出知识库中的某个相关细节来回答。适用于需要定位到具体位置的问题，例如“介绍表1”等类型的问题'


class BasicDocQA(Assistant):
    """This is an agent for doc QA."""

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = DEFAULT_NAME,
                 description: Optional[str] = DEFAULT_DESC,
                 files: Optional[List[str]] = None,
                 rag_cfg: Optional[Dict] = None):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description,
                         files=files,
                         rag_cfg=rag_cfg)
        self.doc_qa = DocQA(llm=self.llm)

    def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        """This agent using different doc qa prompt with Assistant"""
        # Need to use Memory agent for data management
        *_, last = self.mem.run(messages=messages, **kwargs)
        _ref = last[-1][CONTENT]

        # Use RetrievalQA agent
        # Todo: Prompt engineering
        response = self.doc_qa.run(messages=messages, lang=lang, knowledge=_ref)

        return response
