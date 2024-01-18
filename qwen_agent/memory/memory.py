import copy
import json
from typing import Dict, Iterator, List, Optional, Union

import json5

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE,
                                   ROLE, USER)
from qwen_agent.log import logger
from qwen_agent.prompts import GenKeyword
from qwen_agent.tools import Storage
from qwen_agent.tools.similarity_search import RefMaterialInput
from qwen_agent.utils.utils import has_chinese_chars


class Memory(Agent):
    """
    Memory is special agent for data management
    By default, this memory can use tool: doc_parser and retrieval
    """

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 storage_path: Optional[str] = None):
        function_list = function_list or []
        super().__init__(function_list=['doc_parser', 'retrieval'] +
                         function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description)

        self.storage_path = storage_path or 'default_data_path'
        self.db = Storage()
        self.db.init(self.storage_path)

        self.keygen = GenKeyword(llm=llm)

    def run(self,
            messages: List[Dict] = None,
            **kwargs) -> Iterator[List[Dict]]:
        messages = copy.deepcopy(messages) or []
        query = ''
        if messages and messages[-1][ROLE] == USER:
            query = messages[-1][CONTENT]
        if 'lang' not in kwargs:
            if has_chinese_chars([query, kwargs]):
                kwargs['lang'] = 'zh'
            else:
                kwargs['lang'] = 'en'
        return self._run(messages=messages, **kwargs)

    def _run(self,
             messages: List[Dict],
             max_token: int = 4000,
             lang: str = 'en',
             ignore_cache: bool = False,
             **kwargs) -> Iterator[List[Dict]]:
        query, file = self._parse_last_message(messages)

        # process the file: parse and get
        if file:
            func_args = json.dumps({'url': file}, ensure_ascii=False)
        else:
            func_args = {}
        records = self._call_tool('doc_parser',
                                  func_args,
                                  db=self.db,
                                  ignore_cache=ignore_cache,
                                  **kwargs)

        # retrieval the related part of the query
        if not query:
            # return the processed file
            yield [{ROLE: ASSISTANT, CONTENT: records}]
        else:
            records = json5.loads(records)
            if not records:
                yield [{ROLE: ASSISTANT, CONTENT: ''}]
            else:
                # need to retrieval
                # gen keyword
                try:
                    *_, last = self.keygen.run([{ROLE: USER, CONTENT: query}])
                    keyword = last[-1][CONTENT]
                    logger.info(keyword)
                    keyword_dict = json5.loads(keyword)
                    keyword_dict['text'] = query
                    query_with_keyword = keyword_dict
                except Exception:
                    query_with_keyword = query

                # retrieval related content
                records = [
                    RefMaterialInput(**record)
                    for record in json5.loads(records)
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
            now_ref_list = self._call_tool('retrieval',
                                           json.dumps({'query': query},
                                                      ensure_ascii=False),
                                           doc=record,
                                           max_token=single_max_token)
            _ref_list.append(now_ref_list)
        _ref = ''
        if _ref_list:
            _ref = '\n'.join(_ref_list)
        return _ref

    def _parse_last_message(self, messages: List[Dict]):
        text, file = '', ''
        if messages and messages[-1][ROLE] == USER:
            content = messages[-1][CONTENT]
            if isinstance(content, str):
                text = content
                return text, file
            for item in content:
                text = item.get('text', text)
                file = item.get('file', file)
        return text, file
