import json
from typing import Dict, Iterator, List, Optional, Union

import json5

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE,
                                   ROLE, USER, Message)
from qwen_agent.log import logger
from qwen_agent.prompts import GenKeyword
from qwen_agent.utils.utils import get_file_type, is_local_path


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

        self.system_files = files or []

    def _run(self,
             messages: List[Message],
             max_ref_token: int = 4000,
             lang: str = 'en',
             ignore_cache: bool = False) -> Iterator[List[Message]]:
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
        session_files = self.get_all_files_of_messages(messages)
        files = self.system_files + session_files
        rag_files = []
        for file in files:
            if (file.split('.')[-1].lower() in [
                    'pdf', 'docx', 'pptx'
            ]) or (not is_local_path(file) and get_file_type(file) == 'html'):
                rag_files.append(file)

        if not rag_files:
            yield [Message(ASSISTANT, '', name='memory')]
        else:
            query = ''
            # only retrieval content according to the last user query if exists
            if messages and messages[-1][ROLE] == USER:
                if isinstance(messages[-1][CONTENT], str):
                    query = messages[-1][CONTENT]
                else:
                    for item in messages[-1][CONTENT]:
                        if item.text:
                            query += item.text
            if query:
                # gen keyword
                *_, last = self.keygen.run([Message(USER, query)])
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
                'files': rag_files
            },
                                      ignore_cache=ignore_cache,
                                      max_token=max_ref_token)

            yield [
                Message(ASSISTANT,
                        json.dumps(content, ensure_ascii=False),
                        name='memory')
            ]

    @staticmethod
    def get_all_files_of_messages(messages: List[Message]):
        files = []
        for msg in messages:
            if isinstance(msg[CONTENT], list):
                for item in msg[CONTENT]:
                    if item.file:
                        files.append(item.file)
        return files
