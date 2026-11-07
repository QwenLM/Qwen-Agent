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

import socket
import unicodedata

import pytest

from qwen_agent.tools.retrieval import Retrieval
from qwen_agent.utils.tokenization_qwen import count_tokens, tokenizer


@pytest.fixture(autouse=True)
def offline_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def no_network(*args, **kwargs):
        raise AssertionError('No network allowed')

    monkeypatch.setattr(socket.socket, 'connect', no_network)
    monkeypatch.setattr(socket, 'create_connection', no_network)


@pytest.mark.parametrize('text,budget,start,both,expected', [
    ('𠀀abc', 1, 0, False, ''),
    ('𠀀abc', 3, 0, False, '𠀀'),
    ('𠀀abc', 10, 1, False, 'abc'),
    ('𠀀abc', 3, 1, False, 'abc'),
    ('🧬' * 10, 4, 0, True, '...🧬'),
    ('🧬' * 10, 3, 0, True, '...'),
    ('🧬' * 10, 1, 0, True, ''),
    ('🧬' * 10, 0, 0, True, ''),
    ('0' * 10, 5, 0, False, '00000'),
    ('0' * 10, 5, 0, True, '00...00'),
    ('�<|endoftext|>🧬', 2, 0, False, '�<|endoftext|>'),
    ('cafe\u0301', 100, 0, False, 'café'),
])
def test_truncate_complete_spans(text, budget, start, both, expected):
    result = tokenizer.truncate(text, budget, start_token=start, keep_both_sides=both)
    assert result == expected
    assert count_tokens(result) <= budget


@pytest.mark.parametrize('text', [
    '备注：样本🧬通过测序确认身份；' * 10,
    '𠀀' * 100,
    'การตรวจสอบข้อมูลภาษาไทย ' * 10,
    'العينة محفوظة في المختبر ' * 10,
    'ASCII content remains intact ' * 10,
    'cafe\u0301<|endoftext|>🧬' * 10,
])
@pytest.mark.parametrize('both', [False, True])
@pytest.mark.parametrize('budget', [1, 7, 31])
def test_multilingual_truncation_preserves_characters_and_budget(text, both, budget):
    result = tokenizer.truncate(text, budget, keep_both_sides=both)
    assert '\ufffd' not in result
    assert count_tokens(result) <= budget
    normalized = unicodedata.normalize('NFC', text)
    if both and '...' in result:
        prefix, suffix = result.split('...', 1)
        assert normalized.startswith(prefix)
        assert normalized.endswith(suffix)
    else:
        assert normalized.startswith(result)


@pytest.mark.parametrize('text', ['𠀀' * 4000, '备注：' + '样本🧬通过测序确认身份并保留原始数据；' * 1000])
@pytest.mark.parametrize('query', ['', '样本'])
@pytest.mark.parametrize('keyword_only', [False, True])
def test_default_multifile_retrieval_never_introduces_replacement_characters(tmp_path, text, query, keyword_only):
    files = []
    for index in range(2):
        path = tmp_path / f'report-{index}.txt'
        path.write_text(text, encoding='utf-8')
        files.append(str(path))
    retrieval = Retrieval({'rag_searchers': ['keyword_search']} if keyword_only else {})
    assert retrieval.max_ref_token == 20000
    assert retrieval.parser_page_size == 500
    result = retrieval.call({'query': query, 'files': files})
    assert result
    for document in result:
        for chunk in document['text']:
            assert '\ufffd' not in chunk
            assert unicodedata.normalize('NFC', text).startswith(chunk)
    assert sum(count_tokens(chunk) for doc in result for chunk in doc['text']) <= 20000


def test_model_message_truncation_preserves_complete_characters():
    from qwen_agent.llm.base import _truncate_input_messages_roughly
    from qwen_agent.llm.schema import Message

    message = Message(role='user', content='🧬' * 10)
    result = _truncate_input_messages_roughly([message], max_tokens=4)
    assert result[0].content == '...🧬'
    assert count_tokens(result[0].content) <= 4
    assert message.content == '🧬' * 10
