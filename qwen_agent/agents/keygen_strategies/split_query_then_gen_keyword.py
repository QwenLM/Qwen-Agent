import json
from typing import Dict, Iterator, List, Optional, Union

import json5

from qwen_agent import Agent
from qwen_agent.agents.keygen_strategies.gen_keyword import GenKeyword
from qwen_agent.agents.keygen_strategies.split_query import SplitQuery
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import ASSISTANT, DEFAULT_SYSTEM_MESSAGE, USER, Message
from qwen_agent.tools import BaseTool


class SplitQueryThenGenKeyword(Agent):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 **kwargs):
        super().__init__(function_list, llm, system_message, **kwargs)
        self.split_query = SplitQuery(llm=self.llm)
        self.keygen = GenKeyword(llm=llm)

    def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        query = messages[-1].content

        *_, last = self.split_query.run(messages=messages, lang=lang, **kwargs)
        information = last[-1].content.strip()
        if information.startswith('```json'):
            information = information[len('```json'):]
        if information.endswith('```'):
            information = information[:-3]
        try:
            information = '\n'.join(json5.loads(information)['information']).strip()
            if 0 < len(information) <= len(query):
                query = information
        except Exception:
            query = query
        rsp = []
        for rsp in self.keygen.run([Message(USER, query)]):
            yield rsp

        if rsp:
            keyword = rsp[-1].content.strip()
            if keyword.startswith('```json'):
                keyword = keyword[len('```json'):]
            if keyword.endswith('```'):
                keyword = keyword[:-3]
            try:
                keyword_dict = json5.loads(keyword)
                keyword_dict['text'] = query
                yield [Message(role=ASSISTANT, content=json.dumps(keyword_dict, ensure_ascii=False))]
            except Exception:
                pass
