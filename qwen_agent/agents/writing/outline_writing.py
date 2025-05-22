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

import copy
from typing import Iterator, List

from qwen_agent import Agent
from qwen_agent.llm.schema import CONTENT, Message

PROMPT_TEMPLATE_ZH = """
你是一个写作助手，任务是充分理解参考资料，从而完成写作。
#参考资料：
{ref_doc}

写作标题是：{user_request}

为了完成以上写作任务，请先列出大纲。回复只需包含大纲。大纲的一级标题全部以罗马数字计数。只依据给定的参考资料来写，不要引入其余知识。
"""

PROMPT_TEMPLATE_EN = """
You are a writing assistant. Your task is to complete writing article based on reference materials.

# References:
{ref_doc}

The title is: {user_request}

In order to complete the above writing tasks, please provide an outline first. The reply only needs to include an outline. The first level titles of the outline are all counted in Roman numerals. Write only based on the given reference materials and do not introduce other knowledge.
"""

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}


class OutlineWriting(Agent):

    def _run(self, messages: List[Message], knowledge: str = '', lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)
        messages[-1][CONTENT] = PROMPT_TEMPLATE[lang].format(
            ref_doc=knowledge,
            user_request=messages[-1][CONTENT],
        )
        return self._call_llm(messages)
