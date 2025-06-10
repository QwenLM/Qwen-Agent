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

from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.agents.keygen_strategies.gen_keyword import GenKeyword
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import ASSISTANT, DEFAULT_SYSTEM_MESSAGE, Message
from qwen_agent.log import logger
from qwen_agent.tools import BaseTool
from qwen_agent.utils.utils import merge_generate_cfgs


class SplitQuery(GenKeyword):
    """This agent split the query into information."""
    PROMPT_TEMPLATE_EN = """Please extract the key information fragments that can help retrieval and the task description in the question, and give them in JSON format:
{{"information": ["information fragment 1", "information fragment 2"], "instruction": ["instruction fragment 1", "instruction fragment 2"]}}.
If it is a question, the default task description is: Answer the question

Question: What is MMDET.UTILS?
Result: {{"information": ["What is MMDET.UTILS"], "instruction": ["Answer the question"]}}
Observation: ...

Question: Summarize
Result: {{"information": [], "instruction": ["Summarize"]}}
Observation: ...

Question: Describe in great detail 2.1 DATA, 2.2 TOKENIZATION, 2.3 ARCHITECTURE. Also, can you incorporate the methods from this paper?
Result: {{"information": ["2.1 DATA, 2.2 TOKENIZATION, 2.3 ARCHITECTURE"], "instruction": ["Describe in great detail", "Also, can you incorporate the methods from this paper?"]}}
Observation: ...

Question: Help me count the performance of membership levels.
Result: {{"information": ["the performance of membership levels"], "instruction": ["Help me count"]}}
Observation: ...

Question: {user_request}
Result:
"""

    PROMPT_TEMPLATE_ZH = """请提取问题中的可以帮助检索的重点信息片段和任务描述，以JSON的格式给出：{{"information": ["重点信息片段1", "重点信息片段2"], "instruction": ["任务描述片段1", "任务描述片段2"]}}。
如果是提问，则默认任务描述为：回答问题

Question: MMDET.UTILS是什么
Result: {{"information": ["MMDET.UTILS是什么"], "instruction": ["回答问题"]}}
Observation: ...

Question: 总结
Result: {{"information": [], "instruction": ["总结"]}}
Observation: ...

Question: 要非常详细描述2.1 DATA，2.2 TOKENIZATION，2.3 ARCHITECTURE。另外你能把这篇论文的方法融合进去吗
Result: {{"information": ["2.1 DATA，2.2 TOKENIZATION，2.3 ARCHITECTURE"], "instruction": ["要非常详细描述", "另外你能把这篇论文的方法融合进去吗"]}}
Observation: ...

Question: 帮我统计不同会员等级的业绩
Result: {{"information": ["会员等级的业绩"], "instruction": ["帮我统计"]}}
Observation: ...

Question: {user_request}
Result:
"""

    PROMPT_TEMPLATE = {
        'zh': PROMPT_TEMPLATE_ZH,
        'en': PROMPT_TEMPLATE_EN,
    }

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 **kwargs):
        super().__init__(function_list, llm, system_message, **kwargs)
        # Currently, instruction is not utilized,
        # so in order to avoid generating redundant tokens, set 'instruction' as stop words
        self.extra_generate_cfg = merge_generate_cfgs(
            base_generate_cfg=self.extra_generate_cfg,
            new_generate_cfg={'stop': ['"], "instruction":']},
        )

    def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        for last in super()._run(messages=messages, lang=lang, **kwargs):
            continue
        extracted_content = last[-1].content.strip()
        logger.info(f'Extracted info from query: {extracted_content}')
        if extracted_content.endswith('}') or extracted_content.endswith('```'):
            yield [Message(role=ASSISTANT, content=extracted_content)]
        else:
            try:
                extracted_content += '"]}'
                yield [Message(role=ASSISTANT, content=extracted_content)]
            except Exception:
                yield [Message(role=ASSISTANT, content='')]
