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
你是一个写作助手，任务是依据参考资料，完成写作任务。
#参考资料：
{ref_doc}

写作标题是：{user_request}
大纲是：
{outline}

此时你的任务是扩写第{index}个一级标题对应的章节：{capture}。注意每个章节负责撰写不同的内容，所以你不需要为了全面而涵盖之后的内容。请不要在这里生成大纲。只依据给定的参考资料来写，不要引入其余知识。
"""

PROMPT_TEMPLATE_EN = """
You are a writing assistant. Your task is to complete writing article based on reference materials.

# References:
{ref_doc}

The title is: {user_request}

The outline is:
{outline}

At this point, your task is to expand the chapter corresponding to the {index} first level title: {capture}.
Note that each chapter is responsible for writing different content, so you don't need to cover the following content. Please do not generate an outline here. Write only based on the given reference materials and do not introduce other knowledge.
"""

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}


class ExpandWriting(Agent):

    def _run(self,
             messages: List[Message],
             knowledge: str = '',
             outline: str = '',
             index: str = '1',
             capture: str = '',
             capture_later: str = '',
             lang: str = 'en',
             **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)
        prompt = PROMPT_TEMPLATE[lang].format(
            ref_doc=knowledge,
            user_request=messages[-1][CONTENT],
            index=index,
            outline=outline,
            capture=capture,
        )
        if capture_later:
            if lang == 'zh':
                prompt = prompt + '请在涉及 ' + capture_later + ' 时停止。'
            elif lang == 'en':
                prompt = prompt + ' Please stop when writing ' + capture_later
            else:
                raise NotImplementedError

        messages[-1][CONTENT] = prompt
        return self._call_llm(messages)
