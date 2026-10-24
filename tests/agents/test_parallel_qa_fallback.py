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
from unittest.mock import Mock

import pytest

from qwen_agent.agent import Agent
from qwen_agent.agents.doc_qa.parallel_doc_qa import MAX_RAG_TOKEN_SIZE, ParallelDocQA
from qwen_agent.agents.doc_qa.parallel_doc_qa_summary import ParallelDocQASummary
from qwen_agent.llm.base import ModelServiceError
from qwen_agent.llm.schema import Message
from qwen_agent.utils.tokenization_qwen import count_tokens


class ScriptedModel:
    model = 'offline-keywords'
    model_type = ''

    def __init__(self, chunks=(), error=None):
        self.chunks = chunks
        self.error = error
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append(copy.deepcopy(messages))
        if '# Knowledge Base' in messages[0].content:
            yield [Message('assistant', 'The document answer.')]
            return
        for content in self.chunks:
            yield [Message('assistant', content)]
        if self.error is not None:
            raise self.error


def make_agent(model):
    # Avoid constructing disk caches and document parsers in this offline test.
    agent = ParallelDocQA.__new__(ParallelDocQA)
    Agent.__init__(agent, llm=model, system_message=None)
    agent._get_files = Mock(return_value=['notes.txt'])
    agent.function_map['retrieval'] = Mock()
    agent.function_map['retrieval'].call.return_value = [{'url': 'notes.txt', 'text': ['Relevant passage.']}]
    return agent


@pytest.fixture(params=['A member answer.', 'word ' * (MAX_RAG_TOKEN_SIZE + 1)], ids=['short', 'long'])
def member_response(request):
    return request.param


@pytest.mark.parametrize('chunks', [(), ('{"keywords_en": ["partial"]}',)], ids=['before-output', 'after-output'])
def test_service_failure_falls_back_to_full_query(chunks, member_response):
    error = ModelServiceError(code='unavailable', message='Offline provider failure')
    model = ScriptedModel(chunks=chunks, error=error)
    agent = make_agent(model)
    messages = [Message('user', 'What does the document say?')]
    original = copy.deepcopy(messages)

    knowledge = agent._retrieve_according_to_member_responses(messages,
                                                              user_question=messages[0].content,
                                                              member_res=member_response)

    retrieval = agent.function_map['retrieval'].call
    assert retrieval.call_count == 1
    assert retrieval.call_args.args[0] == {
        'query': messages[0].content + '\n\n' + member_response,
        'files': ['notes.txt'],
    }
    assert retrieval.call_args.kwargs == {'max_ref_token': MAX_RAG_TOKEN_SIZE, 'parser_page_size': 300}
    assert 'Relevant passage.' in knowledge
    assert messages == original
    assert len(model.calls) == 1
    if count_tokens(member_response) > MAX_RAG_TOKEN_SIZE:
        assert member_response not in model.calls[0][-1].content
    else:
        assert member_response in model.calls[0][-1].content


@pytest.mark.parametrize('fenced', [False, True])
def test_valid_keywords_keep_structured_query(fenced):
    keywords = {'keywords_en': ['document'], 'keywords_zh': ['文档']}
    content = json.dumps(keywords)
    if fenced:
        content = '```json\n' + content + '\n```'
    agent = make_agent(ScriptedModel(chunks=[content]))

    agent._retrieve_according_to_member_responses([Message('user', 'Question')],
                                                  user_question='Question',
                                                  member_res='Member answer')

    query = json.loads(agent.function_map['retrieval'].call.call_args.args[0]['query'])
    assert query == dict(keywords, text='Question\n\nMember answer')


def test_malformed_keywords_keep_existing_fallback(member_response):
    agent = make_agent(ScriptedModel(chunks=['invalid JSON']))

    agent._retrieve_according_to_member_responses([Message('user', 'Question')],
                                                  user_question='Question',
                                                  member_res=member_response)

    assert agent.function_map['retrieval'].call.call_args.args[0]['query'] == 'Question\n\n' + member_response


def test_unrelated_failure_is_not_swallowed():
    error = RuntimeError('unexpected failure')
    agent = make_agent(ScriptedModel(error=error))

    with pytest.raises(RuntimeError) as caught:
        agent._retrieve_according_to_member_responses([Message('user', 'Question')], user_question='Question')

    assert caught.value is error
    agent.function_map['retrieval'].call.assert_not_called()


def test_public_run_reaches_summary_after_keyword_service_failure():
    model = ScriptedModel(error=ModelServiceError(code='unavailable', message='Offline provider failure'))
    agent = make_agent(model)
    agent._parse_and_chunk_files = Mock(return_value=[{'raw': [{'content': 'Document chunk'}]}])
    agent._ask_member_agent = Mock(return_value=(0, '{"res": "ans", "content": "Member answer"}'))
    agent.summary_agent = ParallelDocQASummary(llm=model)
    messages = [{'role': 'user', 'content': 'Question'}]

    responses = list(agent.run(messages))

    assert responses[-1][-1]['content'] == 'The document answer.'
    assert len(model.calls) == 2
    assert 'Relevant passage.' in model.calls[1][0].content
    assert agent.function_map['retrieval'].call.call_args.args[0]['query'] == 'Question\n\nMember answer'
    assert messages == [{'role': 'user', 'content': 'Question'}]
