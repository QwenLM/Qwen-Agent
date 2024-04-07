import json
from typing import Dict, Iterator, List, Optional, Union

import json5

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import (ASSISTANT, DEFAULT_SYSTEM_MESSAGE, USER,
                                   Message)
from qwen_agent.log import logger
from qwen_agent.prompts import GenKeyword
from qwen_agent.tools import BaseTool
from qwen_agent.utils.utils import get_file_type


class Memory(Agent):
    """Memory is special agent for file management.

    By default, this memory can use retrieval tool for RAG.
    """

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict,
                                                    BaseTool]]] = None,
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
        """This agent is responsible for processing the input files in the message.

         This method stores the files in the knowledge base, and retrievals the relevant parts
         based on the query and returning them.
         The currently supported file types include: .pdf, .docx, .pptx, and html.

         Args:
             messages: A list of messages.
             max_ref_token: Search window for reference materials.
             lang: Language.
             ignore_cache: Whether to reparse the same files.

        Yields:
            The message of retrieved documents.
        """
        # process files in messages
        session_files = self.get_all_files_of_messages(messages)
        files = self.system_files + session_files
        rag_files = []
        for file in files:
            if (file.split('.')[-1].lower() in [
                    'pdf', 'docx', 'pptx'
            ]) or get_file_type(file) == 'html':
                rag_files.append(file)

        if not rag_files:
            yield [Message(role=ASSISTANT, content='', name='memory')]
        else:
            query = ''
            # Only retrieval content according to the last user query if exists
            if messages and messages[-1].role == USER:
                if isinstance(messages[-1].content, str):
                    query = messages[-1].content
                else:
                    for item in messages[-1].content:
                        if item.text:
                            query += item.text
            if query:
                # Gen keyword
                *_, last = self.keygen.run([Message(USER, query)])
                keyword = last[-1].content
                try:
                    logger.info(keyword)
                    keyword_dict = json5.loads(keyword)
                    keyword_dict['text'] = query
                    query = json.dumps(keyword_dict, ensure_ascii=False)
                except Exception:
                    query = query

            content = self._call_tool('retrieval', {
                'query': query,
                'files': rag_files
            },
                                      ignore_cache=ignore_cache,
                                      max_token=max_ref_token)

            yield [Message(role=ASSISTANT, content=content, name='memory')]

    @staticmethod
    def get_all_files_of_messages(messages: List[Message]):
        files = []
        for msg in messages:
            if isinstance(msg.content, list):
                for item in msg.content:
                    if item.file and item.file not in files:
                        files.append(item.file)
        return files
