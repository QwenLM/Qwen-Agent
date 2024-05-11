from typing import List, Literal

# Settings for LLMs
DEFAULT_MAX_INPUT_TOKENS: int = 5800  # The LLM will truncate the input messages if they exceed this limit

# Settings for agents
MAX_LLM_CALL_PER_RUN: int = 8

# Settings for tools
DEFAULT_WORKSPACE: str = 'workspace'

# Settings for RAG
DEFAULT_MAX_REF_TOKEN: int = 4000  # The window size reserved for RAG materials
DEFAULT_PARSER_PAGE_SIZE: int = 500  # Max tokens per chunk when doing RAG
DEFAULT_RAG_KEYGEN_STRATEGY: Literal['none', 'simple', 'vocab'] = 'simple'
DEFAULT_RAG_SEARCHERS: List[str] = ['keyword_search', 'front_page_search']  # Sub-searchers for hybrid retrieval
