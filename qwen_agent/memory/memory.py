import copy
from typing import Dict, Iterator, List, Optional, Union

import json5

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE,
                                   ROLE, USER)
from qwen_agent.log import logger
from qwen_agent.prompts import GenKeyword
from qwen_agent.utils.utils import has_chinese_chars


class Memory(Agent):
    """
    Memory is special agent for data management
    By default, this memory can use tool: retrieval
    """

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 files: Optional[List[str]] = None):
        function_list = function_list or []
        super().__init__(function_list=['retrieval'] + function_list,
                         llm=llm,
                         system_message=system_message)

        self.keygen = GenKeyword(llm=llm)

        self.files = files or []

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
             max_ref_token: int = 4000,
             lang: str = 'en',
             ignore_cache: bool = False) -> Iterator[List[Dict]]:
        """
        :param messages:
        - there are files: need parse and save
        - there are query(in last message): need retrieve and return retrieved text
        :param max_ref_token: the max tokens for retrieved text
        :param lang: point the language if necessary
        :param ignore_cache: parse again
        :return:
        """
        # process files in messages
        files = self._get_all_files_of_messages(messages)
        self.files.extend(files)

        if not self.files:
            yield [{ROLE: ASSISTANT, CONTENT: ''}]
        else:
            query = ''
            # only retrieval content according to the last user query if exists
            if messages and messages[-1][ROLE] == USER:
                if isinstance(messages[-1][CONTENT], str):
                    query = messages[-1][CONTENT]
                else:
                    for item in messages[-1][CONTENT]:
                        query = item.get('text', query)
            if query:
                # gen keyword
                *_, last = self.keygen.run([{ROLE: USER, CONTENT: query}])
                keyword = last[-1][CONTENT]
                try:
                    logger.info(keyword)
                    keyword_dict = json5.loads(keyword)
                    keyword_dict['text'] = query
                    query = keyword_dict
                except Exception:
                    query = query

            content = self._call_tool('retrieval', {
                'query': query,
                'files': self.files
            },
                                      ignore_cache=ignore_cache,
                                      max_token=max_ref_token)

            yield [{ROLE: ASSISTANT, CONTENT: content}]

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
