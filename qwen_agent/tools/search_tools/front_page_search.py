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
