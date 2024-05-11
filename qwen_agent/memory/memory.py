import json
from typing import Dict, Iterator, List, Literal, Optional, Union

import json5

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import ASSISTANT, DEFAULT_SYSTEM_MESSAGE, USER, Message
from qwen_agent.log import logger
from qwen_agent.prompts import GenKeyword
from qwen_agent.settings import (DEFAULT_MAX_REF_TOKEN, DEFAULT_PARSER_PAGE_SIZE, DEFAULT_RAG_KEYGEN_STRATEGY,
                                 DEFAULT_RAG_SEARCHERS)
from qwen_agent.tools import BaseTool
from qwen_agent.tools.simple_doc_parser import PARSER_SUPPORTED_FILE_TYPES
from qwen_agent.utils.utils import extract_files_from_messages, extract_text_from_message, get_file_type


class Memory(Agent):
    """Memory is special agent for file management.

    By default, this memory can use retrieval tool for RAG.
    """

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 files: Optional[List[str]] = None,
                 rag_cfg: Optional[Dict] = None):
        """Initialization the memory.

        Args:
            rag_cfg: The config for RAG. One example is:
              {'max_ref_token': 4000,
              'parser_page_size': 500,
              'rag_keygen_strategy': 'simple',
              'rag_searchers': ['keyword_search', 'front_page_search']}.
              And the above is the default settings.
        """
        self.cfg = rag_cfg or {}
        self.max_ref_token: int = self.cfg.get('max_ref_token', DEFAULT_MAX_REF_TOKEN)
        self.parser_page_size: int = self.cfg.get('parser_page_size', DEFAULT_PARSER_PAGE_SIZE)
        self.rag_searchers = self.cfg.get('rag_searchers', DEFAULT_RAG_SEARCHERS)

        self.rag_keygen_strategy: Literal['none', 'simple', 'vocab'] = self.cfg.get('rag_keygen_strategy',
                                                                                    DEFAULT_RAG_KEYGEN_STRATEGY)

        function_list = function_list or []
        super().__init__(function_list=[{
            'name': 'retrieval',
            'max_ref_token': self.max_ref_token,
            'parser_page_size': self.parser_page_size,
            'rag_searchers': self.rag_searchers,
        }, {
            'name': 'doc_parser',
            'max_ref_token': self.max_ref_token,
            'parser_page_size': self.parser_page_size,
        }] + function_list,
                         llm=llm,
                         system_message=system_message)

        self.system_files = files or []

    def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        """This agent is responsible for processing the input files in the message.

         This method stores the files in the knowledge base, and retrievals the relevant parts
         based on the query and returning them.
         The currently supported file types include: .pdf, .docx, .pptx, .txt, and html.

         Args:
             messages: A list of messages.
             lang: Language.

        Yields:
            The message of retrieved documents.
        """
        # Compatible with the parameter passing of the qwen-agent version <= 0.0.3
        rag_keygen_strategy = kwargs.get('rag_keygen_strategy', self.rag_keygen_strategy)

        # process files in messages
        rag_files = self.get_rag_files(messages)

        if not rag_files:
            yield [Message(role=ASSISTANT, content='', name='memory')]
        else:
            query = ''
            # Only retrieval content according to the last user query if exists
            if messages and messages[-1].role == USER:
                query = extract_text_from_message(messages[-1], add_upload_info=False)
            if query and rag_keygen_strategy != 'none':
                if rag_keygen_strategy == 'vocab':
                    raise NotImplementedError  # WIP
                elif rag_keygen_strategy == 'simple':
                    # Gen keyword
                    keygen = GenKeyword(llm=self.llm)
                    *_, last = keygen.run([Message(USER, query)])
                else:
                    raise NotImplementedError

                keyword = last[-1].content
                keyword = keyword.strip()
                if keyword.startswith('```json'):
                    keyword = keyword[len('```json'):]
                if keyword.endswith('```'):
                    keyword = keyword[:-3]
                try:
                    logger.info(keyword)
                    keyword_dict = json5.loads(keyword)
                    keyword_dict['text'] = query
                    query = json.dumps(keyword_dict, ensure_ascii=False)
                except Exception:
                    query = query

            content = self._call_tool(
                'retrieval',
                {
                    'query': query,
                    'files': rag_files
                },
                **kwargs,
            )

            yield [Message(role=ASSISTANT, content=content, name='memory')]

    def get_rag_files(self, messages: List[Message]):
        session_files = extract_files_from_messages(messages, include_images=False)
        files = self.system_files + session_files
        rag_files = []
        for file in files:
            f_type = get_file_type(file)
            if f_type in PARSER_SUPPORTED_FILE_TYPES and file not in rag_files:
                rag_files.append(file)
        return rag_files
