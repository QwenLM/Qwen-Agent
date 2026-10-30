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
import json
import socket
from unittest.mock import Mock

import pytest

from qwen_agent.agent import Agent
from qwen_agent.agents.doc_qa import parallel_doc_qa
from qwen_agent.agents.doc_qa.parallel_doc_qa import MAX_NO_RESPONSE_RETRY, ParallelDocQA
from qwen_agent.agents.doc_qa.parallel_doc_qa_summary import ParallelDocQASummary
from qwen_agent.llm.schema import Message
from qwen_agent.utils.parallel_executor import parallel_exec


@pytest.fixture(autouse=True)
def no_network(monkeypatch):

    def fail(*args, **kwargs):
        raise AssertionError('These tests must not connect to a provider or document server')

    monkeypatch.setattr(socket.socket, 'connect', fail)
    monkeypatch.setattr(socket, 'create_connection', fail)


class ScriptedModel:

    def __init__(self, first_response, second_response):
        self.responses = {'first excerpt': first_response, 'second excerpt': second_response}
        self.member_calls = []
        self.keyword_calls = []
        self.summary_calls = []

    def chat(self, messages, **kwargs):
        prompt = messages[-1].content
        if '# Document:' in prompt:
            excerpt = next(text for text in self.responses if text in prompt)
            self.member_calls.append(excerpt)
            # The member consumes the final streamed response.
            yield [Message('assistant', 'partial')]
            yield [Message('assistant', self.responses[excerpt])]
        elif 'Keywords:' in prompt:
            self.keyword_calls.append(copy.deepcopy(messages))
            yield [Message('assistant', '{"keywords_en": ["document"]}')]
        elif '# Knowledge Base' in messages[0].content:
            self.summary_calls.append(copy.deepcopy(messages))
            yield [Message('assistant', 'The document answer.')]
        else:
            raise AssertionError(f'Unexpected prompt: {prompt}')


def make_agent(model, monkeypatch):
    # Supply already-parsed tiny documents; retain native member, keyword and
    # summary agents and the real thread-pool executor.
    agent = ParallelDocQA.__new__(ParallelDocQA)
    Agent.__init__(agent, llm=model, system_message=None)
    agent._parse_and_chunk_files = Mock(return_value=[{
        'raw': [{
            'content': 'first excerpt'
        }, {
            'content': 'second excerpt'
        }]
    }])
    agent._get_files = Mock(return_value=['notes.txt'])
    agent.function_map['retrieval'] = Mock()
    agent.function_map['retrieval'].call.return_value = [{'url': 'notes.txt', 'text': ['Document evidence.']}]
    agent.summary_agent = ParallelDocQASummary(llm=model)

    def bounded_parallel(fn, arguments, **kwargs):
        return parallel_exec(fn, arguments, max_workers=2, jitter=0)

    monkeypatch.setattr(parallel_doc_qa, 'parallel_exec', bounded_parallel)
    return agent


@pytest.mark.parametrize('payload, expected', [
    ('null', 'null'),
    ('true', 'true'),
    ('42', '42'),
    ('1.5', '1.5'),
    ('["res", "content"]', '[res, content]'),
    ('"res content"', 'res content'),
])
@pytest.mark.parametrize('fenced', [False, True])
def test_non_object_member_json_uses_text_fallback(payload, expected, fenced, monkeypatch):
    if fenced:
        payload = '```json\n' + payload + '\n```'
        expected = '```json\n' + expected + '\n```'
    model = ScriptedModel(payload, '{"res": "ans", "content": "Second answer."}')
    agent = make_agent(model, monkeypatch)
    messages = [{'role': 'user', 'content': 'What does the document say?'}]
    original = copy.deepcopy(messages)

    responses = list(agent.run(messages))

    assert responses[-1][-1]['content'] == 'The document answer.'
    query = json.loads(agent.function_map['retrieval'].call.call_args.args[0]['query'])
    assert query['text'] == messages[0]['content'] + '\n\n' + expected + '\n\nSecond answer.'
    assert sorted(model.member_calls) == ['first excerpt', 'second excerpt']
    assert len(model.keyword_calls) == len(model.summary_calls) == 1
    assert 'Document evidence.' in model.summary_calls[0][0].content
    assert messages == original


@pytest.mark.parametrize('payload, expected', [
    ('{"res": "ans", "content": " First answer. "}', 'First answer.'),
    ('The first passage.', 'The first passage.'),
    ('[]', '[]'),
    ('"ordinary"', 'ordinary'),
])
def test_existing_member_answer_paths(payload, expected, monkeypatch):
    model = ScriptedModel(payload, '{"res": "ans", "content": "Second answer."}')
    agent = make_agent(model, monkeypatch)

    responses = list(agent.run([{'role': 'user', 'content': 'Question'}]))

    assert responses[-1][-1]['content'] == 'The document answer.'
    query = json.loads(agent.function_map['retrieval'].call.call_args.args[0]['query'])
    assert query['text'] == 'Question\n\n' + expected + '\n\nSecond answer.'
    assert len(model.member_calls) == 2


def test_no_answer_objects_keep_bounded_retries(monkeypatch):
    no_answer = '{"res": "none", "content": "<None>"}'
    model = ScriptedModel(no_answer, no_answer)
    agent = make_agent(model, monkeypatch)

    responses = list(agent.run([{'role': 'user', 'content': 'Question'}]))

    assert responses[-1][-1]['content'] == 'The document answer.'
    query = json.loads(agent.function_map['retrieval'].call.call_args.args[0]['query'])
    assert query['text'] == 'Question\n\n'
    assert len(model.member_calls) == 2 * MAX_NO_RESPONSE_RETRY
    assert len(model.keyword_calls) == len(model.summary_calls) == 1
