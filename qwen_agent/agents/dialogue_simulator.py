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
from typing import Iterator, List, Optional

from qwen_agent.agent import Agent
from qwen_agent.agents.human_simulator import STOP, HumanSimulator
from qwen_agent.llm.schema import ASSISTANT, FUNCTION, SYSTEM, USER, Message


class DialogueSimulator(Agent):

    def __init__(self, user_agent: HumanSimulator, assistant_agent: Agent, max_round: Optional[int] = 5, **kwargs):
        super().__init__(**kwargs)
        self.max_round = max_round
        self.user_agent = user_agent
        self.assistant_agent = assistant_agent

    def _run(self, messages: List[Message] = None, **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)
        response = []
        for i in range(self.max_round):
            if (not messages) or (messages[-1].role == 'assistant'):
                # User speak
                *_, last = self.user_agent.run(messages=_swap_roles(messages), **kwargs)
                last = _swap_roles(last)
                assert len(last) == 1
                assert last[-1].role == 'user'
                if STOP in last[-1].content:
                    break
                messages.extend(last)
                response.extend(last)
                yield response
            if messages and (messages[-1].role == 'user'):
                # Assistant speak
                *_, last = self.assistant_agent.run(messages=messages, **kwargs)
                messages.extend(last)
                response.extend(last)
                yield response
        yield response


def _swap_roles(messages: List[Message]) -> List[Message]:
    new_messages = []
    for msg in copy.deepcopy(messages):
        if msg.role == SYSTEM:
            pass
        elif msg.role == USER:
            msg.role = ASSISTANT
        elif msg.role == ASSISTANT:
            msg.role = USER
            msg.function_call = None
        elif msg.role == FUNCTION:
            continue
        else:
            raise ValueError
        if msg.content:
            new_messages.append(msg)
    return new_messages
