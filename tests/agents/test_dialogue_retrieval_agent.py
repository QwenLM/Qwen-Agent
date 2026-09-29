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
import datetime
import types
from unittest.mock import patch

from qwen_agent.agents import DialogueRetrievalAgent
from qwen_agent.agents import dialogue_retrieval_agent as dialogue_module
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import Message


class RecordingModel(BaseChatModel):
    """Offline model that records the system prompt it is asked with."""

    def __init__(self):
        super().__init__({'model': 'offline-recording-model'})
        self.knowledge_prompt = ''

    def _chat_no_stream(self, messages, generate_cfg):
        system = '\n'.join(str(m.content) for m in messages if m.role == 'system')
        if '# Knowledge Base' in system:
            self.knowledge_prompt = system
            answer = 'recorded'
        else:
            answer = '{"keywords_en": ["stored", "fact"], "keywords_zh": []}'
        return [Message(role='assistant', content=answer)]

    def _chat_stream(self, messages, delta_stream, generate_cfg):
        yield self._chat_no_stream(messages, generate_cfg)

    def _chat_with_functions(self, messages, functions, stream, delta_stream, generate_cfg, lang):
        raise AssertionError('No function tools are configured')


class FixedClock(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 29, 12, 0, 0)


def conversation(marker):
    return [
        {'role': 'user', 'content': f'My stored fact is {marker}.'},
        {'role': 'assistant', 'content': 'Acknowledged.'},
        {'role': 'user', 'content': 'What is my stored fact?'},
    ]


def test_independent_same_second_runs_keep_their_own_history(tmp_path, monkeypatch):
    """Two same-second runs must not share one history file (issue #985).

    The history filename used a second-resolution timestamp only, so two
    independent runs with the default ``session_id`` starting in the same
    second wrote to — and cached their documents under — the same path. The
    document cache then served the first conversation's history to the
    second run's model prompt.
    """
    monkeypatch.setattr(dialogue_module, 'datetime', types.SimpleNamespace(datetime=FixedClock))
    monkeypatch.setattr(dialogue_module, 'DEFAULT_WORKSPACE', str(tmp_path))

    model_a, model_b = RecordingModel(), RecordingModel()
    agent_a = DialogueRetrievalAgent(llm=model_a)
    agent_b = DialogueRetrievalAgent(llm=model_b)

    list(agent_a.run(conversation('A_ONLY')))
    list(agent_b.run(conversation('B_ONLY')))

    assert 'B_ONLY' in model_b.knowledge_prompt
    assert 'A_ONLY' not in model_b.knowledge_prompt


def test_same_second_runs_write_distinct_history_files(tmp_path, monkeypatch):
    """Same-second runs must write distinct history file paths."""
    monkeypatch.setattr(dialogue_module, 'datetime', types.SimpleNamespace(datetime=FixedClock))
    monkeypatch.setattr(dialogue_module, 'DEFAULT_WORKSPACE', str(tmp_path))

    agent_a = DialogueRetrievalAgent(llm=RecordingModel())
    agent_b = DialogueRetrievalAgent(llm=RecordingModel())
    list(agent_a.run(conversation('A')))
    list(agent_b.run(conversation('B')))

    written = [p for p in tmp_path.iterdir() if p.name.startswith('dialogue_history_')]
    assert len(written) == 2
    assert len({p.name for p in written}) == 2
