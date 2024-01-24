import copy
import json
import os
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
from qwen_agent.utils.utils import (has_chinese_chars,
                                    save_url_to_local_work_dir)


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
                 storage_path: Optional[str] = None,
                 files: Optional[List[str]] = None):
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

        self.files = []
        if files:
            for file in files:
                self._cache_file(file)
                self.files.append(file)

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
        """
        :param messages:
        - there are files: need parse and save
        - there are query(in last message): need retrieve and return retrieved text
        :param max_token: the max tokens for retrieved text
        :param lang: point the language if necessary
        :param ignore_cache: parse again
        :param kwargs: some possible additional parameters for doc_parser
        :return:
        """
        query = ''
        current_file = ''
        # only consider the last user query if exists
        if messages and messages[-1][ROLE] == USER:
            if isinstance(messages[-1][CONTENT], str):
                query = messages[-1][CONTENT]
            else:
                for item in messages[-1][CONTENT]:
                    query = item.get('text', query)
                    current_file = item.get('file', current_file)

        # process files in messages: parse and save
        files = self._get_all_files_of_messages(messages)
        for file in files:
            self._cache_file(
                file, ignore_cache=ignore_cache,
                **kwargs)  # Non-duplicate parsing of files in chat
            self.files.append(file)
        logger.debug(current_file)
        print(messages)
        if current_file:
            # Todo: Temporary plan
            logger.info('latest message has file, so filter data by this file')
            records = self._call_tool('doc_parser',
                                      db=self.db,
                                      files=[current_file])

        elif self.files:
            logger.info('filter data by self.files list')
            records = self._call_tool('doc_parser',
                                      db=self.db,
                                      files=self.files)
        elif 'time_limit' in kwargs or 'checked' in kwargs:
            # Todo: This is a temporary plan
            logger.info('filter data by other conditions')
            records = self._call_tool('doc_parser', db=self.db, **kwargs)
        else:
            records = ''

        # retrieval the related part of the query
        if not query or not records:
            # return the processed file
            yield [{ROLE: ASSISTANT, CONTENT: records}]
        else:
            records = json5.loads(records)
            if not records:
                yield [{ROLE: ASSISTANT, CONTENT: ''}]
            else:
                # need to retrieval
                # gen keyword

                *_, last = self.keygen.run([{ROLE: USER, CONTENT: query}])
                keyword = last[-1][CONTENT]
                try:
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
                content = self._retrieve_content(query_with_keyword,
                                                 records=records,
                                                 max_token=max_token)
                logger.debug(
                    json.dumps([{
                        ROLE: ASSISTANT,
                        CONTENT: content
                    }],
                               ensure_ascii=False))
                yield [{ROLE: ASSISTANT, CONTENT: content}]

    def _retrieve_content(self,
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

    @staticmethod
    def _parse_last_message(messages: List[Dict]):
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

    def _cache_file(self, file: str, ignore_cache=True, **kwargs):
        # save original file to workspace dir
        # Todo: This is just a temporary solution. Refactor memory: decoupling from tools
        work_dir = os.getenv('M6_CODE_INTERPRETER_WORK_DIR',
                             os.getcwd() + '/ci_workspace/')
        os.makedirs(work_dir, exist_ok=True)
        save_url_to_local_work_dir(file, work_dir)

        # parse file to knowledge base
        if file.lower().endswith(
            ('pdf', 'docx', 'pptx')) or ('type' in kwargs
                                         and kwargs['type'] == 'html'):
            try:
                func_args = json.dumps({'url': file}, ensure_ascii=False)
                _ = self._call_tool('doc_parser',
                                    func_args,
                                    db=self.db,
                                    ignore_cache=ignore_cache,
                                    **kwargs)
            except Exception:
                raise ValueError(f'Failed to parse document {file}.')

    @staticmethod
    def _get_all_files_of_messages(messages: List[Dict]):
        files = []
        for msg in messages:
            if isinstance(msg[CONTENT], list):
                for item in msg[CONTENT]:
                    for k, v in item.items():
                        if k == 'file':
                            files.append(v)
        return files
