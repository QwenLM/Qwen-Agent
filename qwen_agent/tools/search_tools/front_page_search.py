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

import math
from typing import List, Tuple

from qwen_agent.settings import DEFAULT_MAX_REF_TOKEN
from qwen_agent.tools.base import register_tool
from qwen_agent.tools.doc_parser import Record
from qwen_agent.tools.search_tools.base_search import BaseSearch

POSITIVE_INFINITY = math.inf
DEFAULT_FRONT_PAGE_NUM = 2


@register_tool('front_page_search')
class FrontPageSearch(BaseSearch):

    def sort_by_scores(self,
                       query: str,
                       docs: List[Record],
                       max_ref_token: int = DEFAULT_MAX_REF_TOKEN,
                       **kwargs) -> List[Tuple[str, int, float]]:
        if len(docs) > 1:
            # This is a trick for improving performance for one doc
            # It is not recommended to splice multiple documents directly, so return [], which will not effect the rank
            return []

        chunk_and_score = []
        for doc in docs:
            for chunk_id in range(min(DEFAULT_FRONT_PAGE_NUM, len(doc.raw))):
                page = doc.raw[chunk_id]
                if max_ref_token >= page.token * DEFAULT_FRONT_PAGE_NUM * 2:  # Ensure that the first two pages do not fill up the window
                    chunk_and_score.append((doc.url, chunk_id, POSITIVE_INFINITY))
                else:
                    break

        return chunk_and_score
