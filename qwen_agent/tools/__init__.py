from enum import Enum


class SimilaritySearchType(Enum):
    KeyWord = 'keyword'
    QueryMatch = 'querymatch'
    LLM = 'llm'
    Jaccard = 'jaccard'
