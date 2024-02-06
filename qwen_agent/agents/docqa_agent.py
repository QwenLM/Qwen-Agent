from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.agents.assistant import Assistant
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import CONTENT, DEFAULT_SYSTEM_MESSAGE, Message
from qwen_agent.prompts import DocQA


class DocQAAgent(Assistant):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 files: Optional[List[str]] = None):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         files=files)

        self.doc_qa = DocQA(llm=self.llm)

    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             max_ref_token: int = 4000,
             **kwargs) -> Iterator[List[Message]]:

        # need to use Memory agent for data management
        *_, last = self.mem.run(messages=messages,
                                max_ref_token=max_ref_token,
                                **kwargs)
        _ref = last[-1][CONTENT]

        # use RetrievalQA agent
        response = self.doc_qa.run(messages=messages,
                                   lang=lang,
                                   knowledge=_ref)

        return response
