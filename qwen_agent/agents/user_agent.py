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

from qwen_agent.agent import Agent
from qwen_agent.llm.schema import Message

PENDING_USER_INPUT = '<!-- INTERRUPT: PENDING_USER_INPUT -->'


class UserAgent(Agent):

    def _run(self, messages: List[Message], **kwargs) -> Iterator[List[Message]]:
        yield [Message(role='user', content=PENDING_USER_INPUT, name=self.name)]
