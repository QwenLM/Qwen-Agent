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

import json
import os
from typing import Dict, List, Optional, Tuple

from qwen_agent.tools.base import register_tool
from qwen_agent.tools.doc_parser import Record
from qwen_agent.tools.search_tools.base_search import BaseSearch


@register_tool('vector_search')
class VectorSearch(BaseSearch):
    
    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.embeddings = self.cfg.get('embeddings')

    def sort_by_scores(self, query: str, docs: List[Record], **kwargs) -> List[Tuple[str, int, float]]:
        try:
            from langchain_core.documents import Document
        except ImportError:
            try:
                from langchain.schema import Document
            except ImportError:
                raise ImportError('Please install langchain by: `pip install langchain`')
        
        try:
            from langchain_community.vectorstores import FAISS
        except ImportError:
            raise ImportError(
                'Please install langchain_community by: `pip install langchain_community`, '
                'and install faiss by: `pip install faiss-cpu` or `pip install faiss-gpu` (for CUDA supported GPU)')

        # Extract raw query
        try:
            query_json = json.loads(query)
            # This assumes that the user's input will not contain json str with the 'text' attribute
            if 'text' in query_json:
                query = query_json['text']
        except json.decoder.JSONDecodeError:
            pass

        # Plain all chunks from all docs
        all_chunks = []
        for doc in docs:
            for chk in doc.raw:
                all_chunks.append(Document(page_content=chk.content[:2000], metadata=chk.metadata))

        if self.embeddings:
            embeddings = self.embeddings
        else:
            try:
                from langchain_community.embeddings import DashScopeEmbeddings
            except ImportError:
                raise ImportError('Please install langchain_community by: `pip install langchain_community`')
            
            embeddings = DashScopeEmbeddings(model='text-embedding-v1',
                                             dashscope_api_key=os.getenv('DASHSCOPE_API_KEY', ''))
        
        db = FAISS.from_documents(all_chunks, embeddings)
        chunk_and_score = db.similarity_search_with_score(query, k=len(all_chunks))

        return [(chk.metadata['source'], chk.metadata['chunk_id'], score) for chk, score in chunk_and_score]
