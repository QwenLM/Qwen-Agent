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

from abc import abstractmethod
from typing import Dict, List, Optional, Tuple, Union

from pydantic import BaseModel

from qwen_agent.log import logger
from qwen_agent.settings import DEFAULT_MAX_REF_TOKEN
from qwen_agent.tools.base import BaseTool
from qwen_agent.tools.doc_parser import DocParser, Record
from qwen_agent.utils.tokenization_qwen import count_tokens, tokenizer


class RefMaterialOutput(BaseModel):
    """The knowledge data format output from the retrieval"""
    url: str
    text: list

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'text': self.text,
        }


class BaseSearch(BaseTool):
    description = '从给定文档中检索和问题相关的部分'
    parameters = {
        'type': 'object',
        'properties': {
            'query': {
                'description': '问题，需要从文档中检索和这个问题有关的内容',
                'type': 'string',
            }
        },
        'required': ['query'],
    }

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.max_ref_token: int = self.cfg.get('max_ref_token', DEFAULT_MAX_REF_TOKEN)

    def call(self, params: Union[str, dict], docs: List[Union[Record, str, List[str]]] = None, **kwargs) -> list:
        """The basic search algorithm

        Args:
            params: The dict parameters.
            docs: The list of parsed doc, each doc has unique url.

        Returns:
            The list of retrieved chunks from each doc.

        """
        params = self._verify_json_format_args(params)
        # Compatible with the parameter passing of the qwen-agent version <= 0.0.3
        max_ref_token = kwargs.get('max_ref_token', self.max_ref_token)

        # The query is a string that may contain only the original question,
        # or it may be a json string containing the generated keywords and the original question
        query = params['query']
        if not docs:
            return []
        if not query:
            return self._get_the_front_part(docs, max_ref_token)
        new_docs, all_tokens = self.format_docs(docs)
        logger.info(f'all tokens: {all_tokens}')
        if all_tokens <= max_ref_token:
            # Todo: Whether to use full window
            logger.info('use full ref')
            return [
                RefMaterialOutput(url=doc.url, text=[page.content for page in doc.raw]).to_dict() for doc in new_docs
            ]

        return self.search(query=query, docs=new_docs, max_ref_token=max_ref_token)

    def search(self, query: str, docs: List[Record], max_ref_token: int = DEFAULT_MAX_REF_TOKEN) -> list:
        chunk_and_score = self.sort_by_scores(query=query, docs=docs, max_ref_token=max_ref_token)
        return self.get_topk(chunk_and_score=chunk_and_score, docs=docs, max_ref_token=max_ref_token)

    @abstractmethod
    def sort_by_scores(self, query: str, docs: List[Record], **kwargs) -> List[Tuple[str, int, float]]:
        """The function of compute the correlation score

        Args:
            query: The query
            docs: The doc list

        Returns:
            A list of tuples, one tuple is (the doc url, the chunk id, the score).
            Need to sort by score, and the earlier chunk is more relevant to the query.
        """
        raise NotImplementedError

    def get_topk(self,
                 chunk_and_score: List[Tuple[str, int, float]],
                 docs: List[Record],
                 max_ref_token: int = DEFAULT_MAX_REF_TOKEN) -> list:
        available_token = max_ref_token

        docs_retrieved = {}  # [{'url': 'doc id', 'text': ['', '', ...]}]
        docs_map = {}
        for doc in docs:
            docs_map[doc.url] = doc
            docs_retrieved[doc.url] = RefMaterialOutput(url=doc.url, text=[''] * len(doc.raw))

        for doc_id, chunk_id, _ in chunk_and_score:
            if available_token <= 0:
                break
            page = docs_map[doc_id].raw[chunk_id]
            if docs_retrieved[doc_id].text[chunk_id]:
                # Has retrieved
                continue
            if available_token < page.token:
                docs_retrieved[doc_id].text[chunk_id] = tokenizer.truncate(page.content, max_token=available_token)
                break
            docs_retrieved[doc_id].text[chunk_id] = page.content
            available_token -= page.token

        res = []
        for x in docs_retrieved.values():
            x.text = [chk for chk in x.text if chk]
            if x.text:
                res.append(x.to_dict())
        return res

    def format_docs(self, docs: List[Union[Record, str, List[str]]]):

        def format_input_doc(doc: List[str], url: str = '') -> Record:
            new_doc = []
            parser = DocParser()
            for i, x in enumerate(doc):
                page = {'page_num': i, 'content': [{'text': x, 'token': count_tokens(x)}]}
                new_doc.append(page)
            content = parser.split_doc_to_chunk(new_doc, path=url)
            return Record(url=url, raw=content, title='')

        new_docs = []
        all_tokens = 0
        for i, doc in enumerate(docs):
            if isinstance(doc, str):
                doc = [doc]  # Doc with one page
            if isinstance(doc, list):
                doc = format_input_doc(doc, f'doc_{str(i)}')

            if isinstance(doc, Record):
                new_docs.append(doc)
                all_tokens += sum([page.token for page in doc.raw])
            else:
                raise TypeError
        return new_docs, all_tokens

    @staticmethod
    def _get_the_front_part(docs: List[Record], max_ref_token: int = DEFAULT_MAX_REF_TOKEN) -> list:
        single_max_ref_token = int(max_ref_token / len(docs))
        _ref_list = []
        for doc in docs:
            available_token = single_max_ref_token
            text = []
            for page in doc.raw:
                if available_token <= 0:
                    break
                if page.token <= available_token:
                    text.append(page.content)
                    available_token -= page.token
                else:
                    text.append(tokenizer.truncate(page.content, max_token=available_token))
                    break
            logger.info(f'[Get top] Remaining slots: {available_token}')
            now_ref_list = RefMaterialOutput(url=doc.url, text=text).to_dict()
            _ref_list.append(now_ref_list)
        return _ref_list
