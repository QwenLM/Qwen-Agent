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

from qwen_agent.tools.doc_parser import DocParser, Record
from qwen_agent.tools.search_tools.keyword_search import KeywordSearch
from qwen_agent.utils.tokenization_qwen import count_tokens

TEXTS = [
    '𠀀' * 1200,
    '备注：' + '样本🧬通过测序确认身份并保留原始数据；' * 200,
    'Sequence annotation archived for review; ' * 200,
    'cafe\u0301 ' * 1200,
    '记录<|endoftext|>🧬' * 300,
]


@pytest.fixture(autouse=True)
def offline_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def no_network(*args, **kwargs):
        raise AssertionError('These regression tests must not access the network')

    monkeypatch.setattr(socket.socket, 'connect', no_network)
    monkeypatch.setattr(socket, 'create_connection', no_network)


def _body(chunk):
    return chunk.content.split('\n', 1)[1]


@pytest.mark.parametrize('text', TEXTS)
@pytest.mark.parametrize('page_size', [500, 511, 1024])
def test_long_sentence_preserves_unicode(text, page_size):
    chunks = DocParser().split_doc_to_chunk(
        [{
            'page_num': 1,
            'content': [{
                'text': text,
                'token': count_tokens(text)
            }]
        }],
        path='report.txt',
        parser_page_size=page_size,
    )
    # These long fragments do not fit the 150-character overlap window.
    assert len(chunks) > 1
    assert ''.join(_body(chunk) for chunk in chunks) == unicodedata.normalize('NFC', text)
    assert all(chunk.token <= page_size for chunk in chunks)
    assert all(chunk.token == count_tokens(_body(chunk)) for chunk in chunks)
    assert [chunk.metadata['chunk_id'] for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.metadata['source'] == 'report.txt' for chunk in chunks)


@pytest.mark.parametrize('extension', ['txt', 'docx'])
@pytest.mark.parametrize('text', TEXTS[:2])
def test_local_file_and_retrieval_keep_source_characters(tmp_path, extension, text):
    path = tmp_path / f'report.{extension}'
    if extension == 'docx':
        from docx import Document
        document = Document()
        document.add_paragraph(text)
        document.save(path)
    else:
        path.write_text(text, encoding='utf-8')

    parser = DocParser({'max_ref_token': 500})
    record = Record(**parser.call({'url': str(path)}))
    assert ''.join(_body(chunk) for chunk in record.raw) == text
    assert parser.call({'url': str(path)}) == record.to_dict()
    # Real BM25 ranking, selecting complete chunks rather than the independent
    # token-truncation path, must not expose replacement characters to the LLM.
    result = KeywordSearch().call({'query': '样本'}, docs=[record], max_ref_token=500)
    assert result
    assert all('\ufffd' not in chunk for doc in result for chunk in doc['text'])


@pytest.mark.parametrize('text,budget', [(' 🧬', 2), ('𠀀', 1), ('�<|endoftext|>🧬', 2)])
def test_complete_token_spans_preserve_tiny_budget_text(text, budget):
    from qwen_agent.tools.doc_parser import _split_long_sentence
    from qwen_agent.utils.tokenization_qwen import tokenizer

    parts = list(_split_long_sentence(text, budget))
    assert ''.join(part for part, _ in parts) == text
    tokens = tokenizer.tokenize(text)
    assert sum(size for _, size in parts) == len(tokens)
    start = 0
    for part, size in parts:
        assert part
        if size > budget:
            # Every earlier token boundary splits the encoded character.
            for index in range(start + 1, start + size):
                assert isinstance(tokens[index], bytes)
                assert tokens[index][0] & 0xc0 == 0x80
        start += size
