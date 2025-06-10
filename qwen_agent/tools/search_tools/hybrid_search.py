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

from typing import Dict, List, Optional, Tuple

from qwen_agent.settings import DEFAULT_RAG_SEARCHERS
from qwen_agent.tools.base import TOOL_REGISTRY, register_tool
from qwen_agent.tools.doc_parser import Record
from qwen_agent.tools.search_tools.base_search import BaseSearch
from qwen_agent.tools.search_tools.front_page_search import POSITIVE_INFINITY


@register_tool('hybrid_search')
class HybridSearch(BaseSearch):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.rag_searchers = self.cfg.get('rag_searchers', DEFAULT_RAG_SEARCHERS)

        if self.name in self.rag_searchers:
            raise ValueError(f'{self.name} can not be in `rag_searchers` = {self.rag_searchers}')
        self.search_objs = [TOOL_REGISTRY[name](cfg) for name in self.rag_searchers]

    def sort_by_scores(self, query: str, docs: List[Record], **kwargs) -> List[Tuple[str, int, float]]:
        chunk_and_score_list = []
        for s_obj in self.search_objs:
            chunk_and_score_list.append(s_obj.sort_by_scores(query=query, docs=docs, **kwargs))

        chunk_score_map = {}
        for doc in docs:
            chunk_score_map[doc.url] = [0] * len(doc.raw)

        for chunk_and_score in chunk_and_score_list:
            for i in range(len(chunk_and_score)):
                doc_id = chunk_and_score[i][0]
                chunk_id = chunk_and_score[i][1]
                score = chunk_and_score[i][2]
                if score == POSITIVE_INFINITY:
                    chunk_score_map[doc_id][chunk_id] = POSITIVE_INFINITY
                else:
                    # TODO: This needs to be adjusted for performance
                    chunk_score_map[doc_id][chunk_id] += 1 / (i + 1 + 60)

        all_chunk_and_score = []
        for k, v in chunk_score_map.items():
            for i, x in enumerate(v):
                all_chunk_and_score.append((k, i, x))
        all_chunk_and_score.sort(key=lambda item: item[2], reverse=True)

        return all_chunk_and_score
