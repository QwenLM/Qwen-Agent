from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.agents.assistant import Assistant
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import CONTENT, DEFAULT_SYSTEM_MESSAGE, Message
from qwen_agent.prompts import DocQA
from qwen_agent.tools import BaseTool


class DocQAAgent(Assistant):
    """This is an agent for doc QA."""

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict,
                                                    BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 files: Optional[List[str]] = None):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description,
                         files=files)

        self.doc_qa = DocQA(llm=self.llm)

    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             max_ref_token: int = 4000,
             **kwargs) -> Iterator[List[Message]]:

        # Need to use Memory agent for data management
        *_, last = self.mem.run(messages=messages,
                                max_ref_token=max_ref_token,
                                **kwargs)
        _ref = last[-1][CONTENT]

        # Use RetrievalQA agent
        response = self.doc_qa.run(messages=messages,
                                   lang=lang,
                                   knowledge=_ref)

        return response
