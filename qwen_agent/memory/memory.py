import json
from typing import Dict, Iterator, List, Optional, Union

import json5

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import ASSISTANT, DEFAULT_SYSTEM_MESSAGE, USER, Message
from qwen_agent.log import logger
from qwen_agent.prompts import GenKeyword
from qwen_agent.settings import DEFAULT_MAX_REF_TOKEN, DEFAULT_PARSER_PAGE_SIZE
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
                 files: Optional[List[str]] = None):
        function_list = function_list or []
        super().__init__(function_list=['retrieval'] + function_list, llm=llm, system_message=system_message)

        self.system_files = files or []

    def _run(self,
             messages: List[Message],
             max_ref_token: int = DEFAULT_MAX_REF_TOKEN,
             parser_page_size: int = DEFAULT_PARSER_PAGE_SIZE,
             lang: str = 'en',
             ignore_cache: bool = False,
             **kwargs) -> Iterator[List[Message]]:
        """This agent is responsible for processing the input files in the message.

         This method stores the files in the knowledge base, and retrievals the relevant parts
         based on the query and returning them.
         The currently supported file types include: .pdf, .docx, .pptx, .txt, and html.

         Args:
             messages: A list of messages.
             max_ref_token: Search window for reference materials.
             lang: Language.
             ignore_cache: Whether to reparse the same files.

        Yields:
            The message of retrieved documents.
        """
        # process files in messages
        session_files = extract_files_from_messages(messages)
        files = self.system_files + session_files
        rag_files = []
        for file in files:
            f_type = get_file_type(file)
            if f_type in PARSER_SUPPORTED_FILE_TYPES and file not in rag_files:
                rag_files.append(file)

        if not rag_files:
            yield [Message(role=ASSISTANT, content='', name='memory')]
        else:
            query = ''
            # Only retrieval content according to the last user query if exists
            if messages and messages[-1].role == USER:
                query = extract_text_from_message(messages[-1], add_upload_info=False)
            if query:
                # Gen keyword
                keygen = GenKeyword(llm=self.llm)
                *_, last = keygen.run([Message(USER, query)])

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
                ignore_cache=ignore_cache,
                max_token=max_ref_token,
                parser_page_size=parser_page_size,
                **kwargs,
            )

            yield [Message(role=ASSISTANT, content=content, name='memory')]
