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

import ast
import os
from typing import List, Literal

# Settings for LLMs
DEFAULT_MAX_INPUT_TOKENS: int = int(os.getenv(
    'QWEN_AGENT_DEFAULT_MAX_INPUT_TOKENS', 58000))  # The LLM will truncate the input messages if they exceed this limit

# Settings for agents
MAX_LLM_CALL_PER_RUN: int = int(os.getenv('QWEN_AGENT_MAX_LLM_CALL_PER_RUN', 20))

# Settings for tools
DEFAULT_WORKSPACE: str = os.getenv('QWEN_AGENT_DEFAULT_WORKSPACE', 'workspace')

# Settings for RAG
DEFAULT_MAX_REF_TOKEN: int = int(os.getenv('QWEN_AGENT_DEFAULT_MAX_REF_TOKEN',
                                           20000))  # The window size reserved for RAG materials
DEFAULT_PARSER_PAGE_SIZE: int = int(os.getenv('QWEN_AGENT_DEFAULT_PARSER_PAGE_SIZE',
                                              500))  # Max tokens per chunk when doing RAG
DEFAULT_RAG_KEYGEN_STRATEGY: Literal['None', 'GenKeyword', 'SplitQueryThenGenKeyword', 'GenKeywordWithKnowledge',
                                     'SplitQueryThenGenKeywordWithKnowledge'] = os.getenv(
                                         'QWEN_AGENT_DEFAULT_RAG_KEYGEN_STRATEGY', 'GenKeyword')
DEFAULT_RAG_SEARCHERS: List[str] = ast.literal_eval(
    os.getenv('QWEN_AGENT_DEFAULT_RAG_SEARCHERS',
              "['keyword_search', 'front_page_search']"))  # Sub-searchers for hybrid retrieval
