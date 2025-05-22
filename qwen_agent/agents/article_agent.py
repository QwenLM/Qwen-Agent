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

from typing import Iterator, List

from qwen_agent.agents.assistant import Assistant
from qwen_agent.agents.write_from_scratch import WriteFromScratch
from qwen_agent.agents.writing import ContinueWriting
from qwen_agent.llm.schema import ASSISTANT, CONTENT, Message


class ArticleAgent(Assistant):
    """This is an agent for writing articles.

    It can write a thematic essay or continue writing an article based on reference materials
    """

    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             full_article: bool = False,
             **kwargs) -> Iterator[List[Message]]:

        # Need to use Memory agent for data management
        *_, last = self.mem.run(messages=messages, **kwargs)
        _ref = last[-1][CONTENT]

        response = []
        if _ref:
            response.append(Message(ASSISTANT, f'>\n> Search for relevant information: \n{_ref}\n'))
            yield response

        if full_article:
            writing_agent = WriteFromScratch(llm=self.llm)
        else:
            writing_agent = ContinueWriting(llm=self.llm)
            response.append(Message(ASSISTANT, '>\n> Writing Text: \n'))
            yield response

        for rsp in writing_agent.run(messages=messages, lang=lang, knowledge=_ref):
            if rsp:
                yield response + rsp
