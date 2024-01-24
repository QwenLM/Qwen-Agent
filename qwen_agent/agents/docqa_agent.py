from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import CONTENT, DEFAULT_SYSTEM_MESSAGE
from qwen_agent.memory import Memory
from qwen_agent.prompts import DocQA


class DocQAAgent(Agent):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 storage_path: Optional[str] = None):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description)

        self.mem = Memory(llm=self.llm, storage_path=storage_path)

        self.doc_qa = DocQA(llm=self.llm)

    def _run(self,
             messages: List[Dict],
             lang: str = 'en',
             max_ref_token: int = 4000,
             **kwargs) -> Iterator[List[Dict]]:

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
