import copy
import json
from typing import Dict, Iterator, List, Optional, Union

import json5

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE,
                                   ROLE)
from qwen_agent.log import logger
from qwen_agent.prompts import GenKeyword
from qwen_agent.tools import SimilaritySearch, Storage
from qwen_agent.tools.similarity_search import RefMaterialInput
from qwen_agent.utils.utils import has_chinese_chars


class Memory(Agent):
    """
    Memory is special agent for data management
    This memory defaults to using tools: Storage and SimilaritySearch; lightagent: GenKeyword
    """

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 storage_path: Optional[str] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 **kwargs):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description)

        self.db = Storage()
        self.db.init(storage_path)

        self.search_tool = SimilaritySearch()

        self.keygen = GenKeyword(llm=llm)
        self.keygen.stream = False

    def run(self,
            messages: List[Dict] = None,
            **kwargs) -> Iterator[List[Dict]]:
        messages = copy.deepcopy(messages) or []
        query = ''
        if messages and messages[-1][ROLE] == ASSISTANT:
            query = messages[-1][ROLE]
        if 'lang' not in kwargs:
            if has_chinese_chars([query, kwargs]):
                kwargs['lang'] = 'zh'
            else:
                kwargs['lang'] = 'en'
        return self._run(messages=messages, **kwargs)

    def _run(self,
             messages: List[Dict],
             url: str = None,
             max_token: int = 4000,
             lang: str = 'en',
             **kwargs) -> Iterator[List[Dict]]:
        # parse doc
        if url:
            func_args = json.dumps({'url': url}, ensure_ascii=False)
        else:
            func_args = {}
        records = self._call_tool('doc_parser',
                                  func_args,
                                  db=self.db,
                                  **kwargs)
        if not messages:
            yield [{ROLE: ASSISTANT, CONTENT: records}]
        else:
            records = json5.loads(records)
            if not records:
                yield [{ROLE: ASSISTANT, CONTENT: ''}]

            # need to retrieval
            # gen keyword
            *_, last = self.keygen.run(messages)
            keyword = last[-1][CONTENT]
            logger.info(keyword)
            try:
                keyword_dict = json5.loads(keyword)
                keyword_dict['text'] = messages[-1][CONTENT]
                query_with_keyword = json.dumps(keyword_dict,
                                                ensure_ascii=False)
            except Exception:
                query_with_keyword = messages[-1][CONTENT]

            # retrieval related content
            records = [
                RefMaterialInput(**record) for record in json5.loads(records)
            ]
            content = self.retrieve_content(query_with_keyword,
                                            records=records,
                                            max_token=max_token)
            logger.debug(
                json.dumps([{
                    ROLE: ASSISTANT,
                    CONTENT: content
                }],
                           ensure_ascii=False))
            yield [{ROLE: ASSISTANT, CONTENT: content}]

    def retrieve_content(self,
                         query: str,
                         records: List[RefMaterialInput],
                         max_token=4000,
                         **kwargs) -> str:
        single_max_token = int(max_token / len(records))
        _ref_list = []
        for record in records:
            # retrieval for query
            now_ref_list = self.search_tool.call({'query': query}, record,
                                                 single_max_token)
            _ref_list.append(now_ref_list)
        _ref = ''
        if _ref_list:
            _ref = '\n'.join(_ref_list)
        return _ref
