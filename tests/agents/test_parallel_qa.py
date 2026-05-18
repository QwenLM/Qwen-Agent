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

import pytest

from qwen_agent.agents.assistant import Assistant
from qwen_agent.agents.doc_qa import ParallelDocQA
from qwen_agent.llm.schema import Message


class DummyLLM:
    model = 'qwen-test'
    model_type = ''


def test_parallel_qa():
    llm_cfg = {'model': 'qwen-max', 'api_key': '', 'model_server': 'dashscope'}
    agent = ParallelDocQA(llm=llm_cfg)
    messages = [{
        'role':
            'user',
        'content': [{
            'text': 'FastAPI适合IO密集任务吗'
        }, {
            'file': 'https://www.runoob.com/fastapi/fastapi-tutorial.html'
        }, {
            'file': 'https://www.runoob.com/fastapi/fastapi-install.html'
        }]
    }]
    *_, last = agent.run(messages)

    assert len(last[-1]['content']) > 0


def test_parallel_qa_without_files_falls_back_to_assistant(monkeypatch):
    def fake_assistant_run(self, messages, lang='en', **kwargs):
        yield [Message('assistant', 'fallback answer')]

    monkeypatch.setattr(Assistant, '_run', fake_assistant_run)

    agent = ParallelDocQA(llm=DummyLLM())
    responses = list(agent._run([Message('user', '你好')], lang='zh'))

    assert responses[-1][-1].content == 'fallback answer'


def test_parallel_qa_keeps_parse_failure_assertion(monkeypatch):
    agent = ParallelDocQA(llm=DummyLLM())
    monkeypatch.setattr(agent, '_get_files', lambda messages: ['bad.pdf'])
    monkeypatch.setattr(agent, '_parse_and_chunk_files', lambda messages: [])

    with pytest.raises(AssertionError, match='records is empty'):
        list(agent._run([Message('user', '总结文档')], lang='zh'))
