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

from qwen_agent.agents.human_simulator import DEFAULT_HUMAN_SIMULATOR_PROMPT, HumanSimulator
from qwen_agent.llm.schema import ASSISTANT, Message


class RecordingChatModel:
    """Minimal stand-in for a chat model that records the prompt it receives."""

    model = 'recording-model'
    model_type = ''

    def __init__(self):
        self.messages = None

    def chat(self, messages, **kwargs):
        self.messages = messages
        return [[Message(ASSISTANT, '["Hello"]')]]


def test_default_system_prompt_is_applied():
    llm = RecordingChatModel()
    agent = HumanSimulator(llm=llm)

    list(agent.run([Message('user', 'start')]))

    assert llm.messages is not None
    assert llm.messages[0].role == 'system'
    assert llm.messages[0].content.startswith(DEFAULT_HUMAN_SIMULATOR_PROMPT)


def test_custom_system_prompt_is_appended_to_default():
    llm = RecordingChatModel()
    agent = HumanSimulator(llm=llm, system_message='Custom instruction.')

    list(agent.run([Message('user', 'start')]))

    assert llm.messages[0].content.startswith(DEFAULT_HUMAN_SIMULATOR_PROMPT)
    assert llm.messages[0].content.endswith('Custom instruction.')
