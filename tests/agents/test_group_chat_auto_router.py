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

from qwen_agent.agent import BasicAgent
from qwen_agent.agents.group_chat_auto_router import GroupChatAutoRouter
from qwen_agent.llm.schema import Message, SYSTEM


def _router_dialogue(monkeypatch, speaker_names):
    names = dict.fromkeys(name for name, _ in speaker_names)
    agents = [BasicAgent(name=name, description='') for name in names]
    router = GroupChatAutoRouter(agents=agents)
    captured = {}

    def stub_call_llm(messages, **kwargs):
        captured['messages'] = messages
        return iter(())

    monkeypatch.setattr(router, '_call_llm', stub_call_llm)
    messages = [Message(SYSTEM, 'system prompt')]
    messages.extend(Message('assistant', content, name=name) for name, content in speaker_names)

    list(router._run(messages))
    return captured['messages'][-1].content


def test_prefix_speaker_names_keep_both_labels(monkeypatch):
    dialogue = _router_dialogue(monkeypatch, [('Anna', 'first'), ('Ann', 'second')])

    assert dialogue == 'Anna: first\nAnn: second'


def test_consecutive_messages_from_same_speaker_are_merged(monkeypatch):
    dialogue = _router_dialogue(monkeypatch, [('Anna', 'first'), ('Anna', 'second')])

    assert dialogue == 'Anna: first\nsecond'
