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

from typing import Dict, List, Optional, Union

from qwen_agent.agents.keygen_strategies.gen_keyword_with_knowledge import GenKeywordWithKnowledge
from qwen_agent.agents.keygen_strategies.split_query_then_gen_keyword import SplitQueryThenGenKeyword
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import DEFAULT_SYSTEM_MESSAGE
from qwen_agent.tools import BaseTool


class SplitQueryThenGenKeywordWithKnowledge(SplitQueryThenGenKeyword):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 **kwargs):
        super().__init__(function_list, llm, system_message, **kwargs)
        self.keygen = GenKeywordWithKnowledge(llm=llm)
