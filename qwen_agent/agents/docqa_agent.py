from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.memory import Memory
from qwen_agent.prompts import RetrievalQA


class DocQAAgent(Agent):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 storage_path: Optional[str] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 **kwargs):
        super().__init__(function_list=function_list,
                         llm=llm,
                         storage_path=storage_path,
                         name=name,
                         description=description)

        self.mem = Memory(function_list=self.function_list,
                          llm=self.llm,
                          storage_path=self.storage_path)
        self.retrieval_qa = RetrievalQA(llm=self.llm)

    def _run(self,
             query: str = None,
             url: str = None,
             max_ref_token: int = 4000,
             history: Optional[List] = None,
             stop: Optional[List[str]] = None,
             lang: str = 'en',
             **kwargs) -> Union[str, Iterator[str]]:

        # need to use Memory agent for data management
        _ref = self.mem.run(query, url, max_ref_token, **kwargs)

        # use RetrievalQA agent
        response = self.retrieval_qa.run(user_request=query, ref_doc=_ref)

        return response
