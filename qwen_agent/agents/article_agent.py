import copy
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE,
                                   ROLE)
from qwen_agent.memory import Memory
from qwen_agent.prompts import ContinueWriting, WriteFromScratch


class ArticleAgent(Agent):

    def __init__(
        self,
        function_list: Optional[List[Union[str, Dict]]] = None,
        llm: Optional[Union[Dict, BaseChatModel]] = None,
        system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
        name: Optional[str] = None,
        description: Optional[str] = None,
        storage_path: Optional[str] = None,
    ):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description)

        self.mem = Memory(llm=self.llm, storage_path=storage_path)

    def _run(self,
             messages: List[Dict],
             url: str = None,
             max_ref_token: int = 4000,
             full_article: bool = False,
             stop: Optional[List[str]] = None,
             lang: str = 'en',
             **kwargs) -> Union[str, Iterator[str]]:

        # need to use Memory agent for data management
        messages_with_file = copy.deepcopy(
            messages)  # this is a temporary plan
        messages_with_file[-1][CONTENT] = [{
            'text': messages[-1][CONTENT]
        }, {
            'file': url
        }]
        *_, last = self.mem.run(messages=messages_with_file,
                                max_ref_token=max_ref_token,
                                **kwargs)
        _ref = last[-1][CONTENT]

        response = []
        if _ref:
            response.append({
                ROLE:
                ASSISTANT,
                CONTENT:
                f'\n========================= \n> Search for relevant information: \n{_ref}\n'
            })
            yield response

        if full_article:
            writing_agent = WriteFromScratch(llm=self.llm)
        else:
            writing_agent = ContinueWriting(llm=self.llm)
            response.append({
                ROLE:
                ASSISTANT,
                CONTENT:
                '\n========================= \n> Writing Text: \n'
            })
            yield response
        res = writing_agent.run(messages=messages, knowledge=_ref)
        for trunk in res:
            yield response + trunk
