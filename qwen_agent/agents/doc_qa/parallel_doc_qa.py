# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import json
import re
import time
from typing import Dict, Iterator, List, Optional, Union

import json5

from qwen_agent.agents.assistant import KNOWLEDGE_SNIPPET, Assistant, format_knowledge_to_source_and_content
from qwen_agent.agents.doc_qa.parallel_doc_qa_member import NO_RESPONSE, ParallelDocQAMember
from qwen_agent.agents.doc_qa.parallel_doc_qa_summary import ParallelDocQASummary
from qwen_agent.agents.keygen_strategies import GenKeyword
from qwen_agent.llm.base import BaseChatModel, ModelServiceError
from qwen_agent.llm.schema import DEFAULT_SYSTEM_MESSAGE, USER, Message
from qwen_agent.log import logger
from qwen_agent.tools import BaseTool
from qwen_agent.tools.doc_parser import DocParser
from qwen_agent.tools.simple_doc_parser import PARSER_SUPPORTED_FILE_TYPES
from qwen_agent.utils.parallel_executor import parallel_exec
from qwen_agent.utils.tokenization_qwen import count_tokens
from qwen_agent.utils.utils import (extract_files_from_messages, extract_text_from_message, get_file_type,
                                    print_traceback)

MAX_NO_RESPONSE_RETRY = 4
DEFAULT_NAME = 'Simple Parallel DocQA With RAG Sum Agents'
DEFAULT_DESC = '简易并行后用RAG召回内容，然后回答的Agent'

PARALLEL_CHUNK_SIZE = 1000  # chunk size param for parallel chunk

MAX_RAG_TOKEN_SIZE = 4500
RAG_CHUNK_SIZE = 300


class ParallelDocQA(Assistant):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = DEFAULT_NAME,
                 description: Optional[str] = DEFAULT_DESC,
                 files: Optional[List[str]] = None):

        function_list = function_list or []
        super().__init__(
            function_list=[{
                'name': 'retrieval',
                'max_ref_token': MAX_RAG_TOKEN_SIZE,
                'parser_page_size': RAG_CHUNK_SIZE,
                'rag_searchers': ['keyword_search']
            }] + function_list,
            llm=llm,
            system_message=system_message,
            name=name,
            description=description,
            files=files,
        )

        self.doc_parse = DocParser()
        self.summary_agent = ParallelDocQASummary(llm=self.llm)

    def _get_files(self, messages: List[Message]):
        session_files = extract_files_from_messages(messages, include_images=False)
        valid_files = []
        for file in session_files:
            f_type = get_file_type(file)
            if f_type in PARSER_SUPPORTED_FILE_TYPES and file not in valid_files:
                valid_files.append(file)
        return valid_files

    def _parse_and_chunk_files(self, messages: List[Message]):
        valid_files = self._get_files(messages)
        records = []
        for file in valid_files:
            # here to split docs, we should decide chunc size by input doc token length
            # if a document's tokens are below this max_ref_token, it will remain unchunked.
            _record = self.doc_parse.call(params={'url': file},
                                          parser_page_size=PARALLEL_CHUNK_SIZE,
                                          max_ref_token=PARALLEL_CHUNK_SIZE)
            records.append(_record)
        return records

    def _retrieve_according_to_member_responses(
        self,
        messages: List[Message],
        lang: str = 'en',
        user_question: str = '',
        member_res: str = '',
    ):
        messages = copy.deepcopy(messages)
        valid_files = self._get_files(messages)

        keygen = GenKeyword(llm=self.llm)
        member_res_token_num = count_tokens(member_res)

        # Limit the token length of keygen input to avoid wasting tokens due to excessively long docqa member output.
        unuse_member_res = member_res_token_num > MAX_RAG_TOKEN_SIZE
        query = user_question if unuse_member_res else f'{user_question}\n\n{member_res}'

        try:
            *_, last = keygen.run([Message(USER, query)])
        except ModelServiceError:
            print_traceback()

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
            if unuse_member_res:
                keyword_dict['text'] += '\n\n' + member_res
            rag_query = json.dumps(keyword_dict, ensure_ascii=False)
        except Exception:
            rag_query = query
            if unuse_member_res:
                rag_query += '\n\n' + member_res

        # max_ref_token is the retrieve doc token size
        # parser_page_size is the chunk size in retrieve

        retrieve_content = self.function_map['retrieval'].call(
            {
                'query': rag_query,
                'files': valid_files
            },
            max_ref_token=MAX_RAG_TOKEN_SIZE,
            parser_page_size=RAG_CHUNK_SIZE,
        )
        if not isinstance(retrieve_content, str):
            retrieve_content = json.dumps(retrieve_content, ensure_ascii=False, indent=4)

        retrieve_content = format_knowledge_to_source_and_content(retrieve_content)

        snippets = []

        for k in retrieve_content:
            snippets.append(KNOWLEDGE_SNIPPET[lang].format(source=k['source'], content=k['content']))

        assert len(snippets) > 0, retrieve_content
        retrieve_res = '\n\n'.join(snippets)
        return retrieve_res

    def _is_none_response(self, text: str) -> bool:
        none_response_list = ['很抱歉', NO_RESPONSE, "\"res\": \"none\""]
        for none_response in none_response_list:
            if none_response in text.lower():
                return True
        return False

    def _extract_text_from_output(self, output):
        # Remove symbols and keywords from the JSON structure using regular expressions
        cleaned_output = re.sub(r'[{}"]|("res":\s*"ans"|"res":\s*"none"|"\s*content":\s*)', '', output)

        # cleaned_output = re.sub(r'\s*,\s*|\{no_response\}', '', cleaned_output).strip()
        return cleaned_output

    def _parser_json(self, content):
        content = content.strip()
        if content.startswith('```json'):
            content = content[len('```json'):]
        if content.endswith('```'):
            content = content[:-3]
        try:
            content_dict = json5.loads(content)
            return True, content_dict
        except Exception:
            return False, content

    def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]:

        messages = copy.deepcopy(messages)
        # Extract User Question
        user_question = extract_text_from_message(messages[-1], add_upload_info=False)
        logger.info('user_question: ' + user_question)

        # Implement chunk strategy for parallel agent
        records = self._parse_and_chunk_files(messages=messages)
        assert len(records) > 0, 'records is empty, all url parsing failed.'

        data = []
        idx = 0
        for record in records:
            assert len(record['raw']) > 0, 'Document content cannot be empty or null.'
            for chunk in record['raw']:
                chunk_text = chunk['content']
                data.append({
                    'index': idx,
                    'messages': messages,
                    'lang': lang,
                    'knowledge': chunk_text,
                    'instruction': user_question,
                })
                idx += 1
        logger.info('Parallel Member Num: ' + str(len(data)))

        # Retry for None in 7b model
        retry_cnt = MAX_NO_RESPONSE_RETRY
        member_res = ''
        while retry_cnt > 0:
            time1 = time.time()
            results = parallel_exec(self._ask_member_agent, data, jitter=0.5)
            # results = serial_exec(self._qa, data)
            time2 = time.time()
            logger.info(f'Finished parallel_exec. Time spent: {time2 - time1} seconds.')
            ordered_results = sorted(results, key=lambda x: x[0])
            filtered_results = []

            for index, text in ordered_results:
                parser_success, parser_json_content = self._parser_json(text)
                if parser_success and ('res' in parser_json_content) and ('content' in parser_json_content):
                    pa_res, pa_cotent = parser_json_content['res'], parser_json_content['content']
                    if (pa_res in ['ans', 'none']) and (isinstance(pa_cotent, str)):
                        if pa_res == 'ans':
                            filtered_results.append((index, pa_cotent.strip()))
                            continue
                        elif pa_res == 'none':
                            continue
                if self._is_none_response(text):
                    continue
                clean_output = self._extract_text_from_output(text)
                filtered_results.append((index, clean_output.strip()))

            if filtered_results:
                member_res = '\n\n'.join(text for index, text in filtered_results)
                break
            retry_cnt -= 1

        retrieve_content = self._retrieve_according_to_member_responses(messages=messages,
                                                                        lang=lang,
                                                                        user_question=user_question,
                                                                        member_res=member_res)
        return self.summary_agent.run(messages=messages, lang=lang, knowledge=retrieve_content)

    def _ask_member_agent(self,
                          index: int,
                          messages: List[Message],
                          lang: str = 'en',
                          knowledge: str = '',
                          instruction: str = '') -> tuple:
        doc_qa = ParallelDocQAMember(llm=self.llm)
        *_, last = doc_qa.run(messages=messages, knowledge=knowledge, lang=lang, instruction=instruction)
        return index, last[-1].content
