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
