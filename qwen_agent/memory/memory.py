import json
from typing import Dict, List, Optional, Union

import json5

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.log import logger
from qwen_agent.prompts import GenKeyword
from qwen_agent.tools import SimilaritySearch, Storage
from qwen_agent.tools.similarity_search import RefMaterialInput


class Memory(Agent):
    """
    Memory is special agent for data management
    This memory defaults to using tools: Storage and SimilaritySearch; lightagent: GenKeyword
    """

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 storage_path: Optional[str] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 **kwargs):
        super().__init__(function_list=function_list,
                         llm=llm,
                         name=name,
                         description=description)

        self.db = Storage()
        self.db.init(storage_path)

        self.search_tool = SimilaritySearch()

        self.keygen = GenKeyword(llm=llm)
        self.keygen.stream = False

    def _run(self,
             query: str = None,
             url: str = None,
             max_token: int = 4000,
             **kwargs):
        # parse doc
        if url:
            func_args = json.dumps({'url': url}, ensure_ascii=False)
        else:
            func_args = {}
        records = self._call_tool('doc_parser',
                                  func_args,
                                  db=self.db,
                                  **kwargs)
        if not query:
            return records
        records = json5.loads(records)
        if not records:
            return ''

        # need to retrieval
        # gen keyword
        keyword = self.keygen.run(query)
        logger.info(keyword)
        try:
            keyword_dict = json5.loads(keyword)
            keyword_dict['text'] = query
            query_with_keyword = keyword_dict
        except Exception:
            query_with_keyword = query

        # retrieval related content
        records = [
            RefMaterialInput(**record) for record in json5.loads(records)
        ]
        content = self.retrieve_content(query_with_keyword,
                                        records=records,
                                        max_token=max_token)
        return content

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
