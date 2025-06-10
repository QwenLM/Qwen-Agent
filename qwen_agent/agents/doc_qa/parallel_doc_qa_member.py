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
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import CONTENT, DEFAULT_SYSTEM_MESSAGE, ROLE, SYSTEM, USER, ContentItem, Message
from qwen_agent.tools import BaseTool
from qwen_agent.utils.utils import merge_generate_cfgs

NO_RESPONSE = '<None>'
SYSTEM_PROMPT_TEMPLATE_ZH = """您是一个擅长文档问答的专家，可以根据文档内容回答用户问题。


# 任务描述：
请仔细阅读所给的文档片段，并根据其内容回答问题。
您需要判断文档的内容是否可以回答问题，不要强行回答。如果可以回答，答案必须严格遵循文档内容，即使与事实不符。
如果答案与事实不符，直接给出答案，不要做解释。


# 回答规则：
- 请使用与文档材料相同的语言回答问题。
- 评估文档是否含有足够信息回答问题。无关时不要回答。
- 如果问题能被回答，你的回答必须严格遵循文档内容，即使与事实不符。一定不要做多余解释。
- 如果问题能被回答，直接引用文档的相关信息保证答案准确、完整，并追求简洁。
- 当文档中只有少量信息与问题相关时，重点关注这部分信息，这种情况下一定回答。


# 回答格式：
回答的内容请以JSON的格式给出。


## 示例：
当文档内容无关时：
{{"res": "none", "content": "{no_response}"}}，
Observation: ...

当文档内容可回答，且文档为中文时：
{{"res": "ans", "content": "你的答案"}}
Observation: ...

当文档内容可回答，且文档为英文时：
{{"res": "ans", "content": "[Your Answer]"}}
Observation: ..."""

SYSTEM_PROMPT_TEMPLATE_EN = """You are an expert in document-based question answering, capable of answering user questions based on document content.


# Task Description:
Please read the provided document excerpt carefully and answer questions based on its content.
You must assess whether the document content allows for the questions to be answered, without forcing a response.
If the answer does not align with the facts, provide it directly without explanation.


# Answering Rules:
- Reply in the same language as the source material.
- Evaluate whether the document contains sufficient information to answer the question. Do not respond if it's irrelevant.
- If the question can be answered, your answer must strictly follow the document content, even if it does not align with the facts.
- If the question can be answered, directly quote the relevant information from the document to ensure the answer is accurate, complete, and strive for conciseness.
- When the document contains only minimal information related to the question, focus on this information and be sure to answer.


# Answer Format:
Please provide answers in the form of JSON.


## Examples
When the document content is irrelevant:
{{"res": "none", "content": "{no_response}"}},
Observation: ...

When the document content can provide an answer:
{{"res": "ans", "content": "[Your Answer]"}}
Observation: ..."""

SYSTEM_PROMPT_TEMPLATE = {
    'zh': SYSTEM_PROMPT_TEMPLATE_ZH,
    'en': SYSTEM_PROMPT_TEMPLATE_EN,
}

PROMPT_TEMPLATE_ZH = """# 文档：
{ref_doc}

# 问题：
{instruction}

请根据回答规则，给出你的回答："""

PROMPT_TEMPLATE_EN = """# Document:
{ref_doc}

# Question:
{instruction}

Please provide your answer according to the answering rules:"""

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}


class ParallelDocQAMember(Agent):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 **kwargs):
        super().__init__(function_list, llm, system_message, **kwargs)
        self.extra_generate_cfg = merge_generate_cfgs(
            base_generate_cfg=self.extra_generate_cfg,
            new_generate_cfg={'stop': ['Observation:', 'Observation:\n']},
        )

    def _run(self,
             messages: List[Message],
             knowledge: str = '',
             lang: str = 'en',
             instruction: str = None,
             **kwargs) -> Iterator[List[Message]]:

        messages = copy.deepcopy(messages)

        system_prompt = SYSTEM_PROMPT_TEMPLATE[lang].format(no_response=NO_RESPONSE)
        if messages and messages[0][ROLE] == SYSTEM:
            if isinstance(messages[0][CONTENT], str):
                messages[0][CONTENT] += '\n\n' + system_prompt
            else:
                assert isinstance(messages[0][CONTENT], list)
                messages[0][CONTENT] += [ContentItem(text='\n\n' + system_prompt)]
        else:
            messages.insert(0, Message(SYSTEM, system_prompt))

        assert len(messages) > 0, messages
        assert messages[-1][ROLE] == USER, messages
        prompt = PROMPT_TEMPLATE[lang].format(ref_doc=knowledge, instruction=instruction)

        messages[-1] = Message(USER, prompt)
        return self._call_llm(messages=messages)
