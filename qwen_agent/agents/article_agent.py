from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.memory import Memory
from qwen_agent.prompts import ContinueWriting, WriteFromScratch


class ArticleAgent(Agent):

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

    def _run(self,
             query: str = None,
             url: str = None,
             max_ref_token: int = 4000,
             full_article: bool = False,
             history: Optional[List] = None,
             stop: Optional[List[str]] = None,
             lang: str = 'en',
             **kwargs) -> Union[str, Iterator[str]]:

        # need to use Memory agent for data management
        _ref = self.mem.run(query, url, max_ref_token, **kwargs)
        if _ref:
            yield '\n========================= \n'
            yield '> Search for relevant information: \n'
            yield _ref
            yield '\n'

        if full_article:
            writing_agent = WriteFromScratch(llm=self.llm)
        else:
            writing_agent = ContinueWriting(llm=self.llm)
            yield '\n========================= \n'
            yield '> Writing Text: \n'
        response = writing_agent.run(user_request=query, ref_doc=_ref)

        for x in response:
            yield x
