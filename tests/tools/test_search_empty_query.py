# Copyright 2026 The Qwen team, Alibaba Group. All rights reserved.
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

from qwen_agent.tools import HybridSearch, KeywordSearch
from qwen_agent.tools.doc_parser import Chunk, Record
from qwen_agent.tools.search_tools.front_page_search import FrontPageSearch
from qwen_agent.utils.tokenization_qwen import count_tokens, tokenizer


@pytest.fixture(params=[KeywordSearch, FrontPageSearch, HybridSearch])
def search_tool(request, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    return request.param()


@pytest.mark.parametrize('doc_type', ['text', 'pages', 'record', 'mixed'])
@pytest.mark.parametrize('max_ref_token', [6, 1000])
def test_empty_query_normalizes_documents(search_tool, doc_type, max_ref_token):
    text = 'alpha beta gamma delta epsilon zeta eta theta iota kappa'
    record = Record(
        url='existing.txt',
        title='Existing document',
        raw=[Chunk(content=text, metadata={
            'source': 'existing.txt',
            'chunk_id': 0
        }, token=count_tokens(text))])
    docs = {
        'text': [text],
        'pages': [[text, text]],
        'record': [record],
        'mixed': [record, text, [text, text]],
    }[doc_type]
    normalized, _ = search_tool.format_docs(docs)
    budget = max_ref_token // len(normalized)
    expected = []
    for doc in normalized:
        # These short documents each fit in a single parser chunk.
        assert len(doc.raw) == 1
        chunk = doc.raw[0]
        content = chunk.content if chunk.token <= budget else tokenizer.truncate(chunk.content, max_token=budget)
        expected.append({'url': doc.url, 'text': [content]})

    assert search_tool.call({'query': ''}, docs=docs, max_ref_token=max_ref_token) == expected


@pytest.mark.parametrize('docs', [None, []])
def test_empty_query_without_documents(search_tool, docs):
    assert search_tool.call({'query': ''}, docs=docs) == []
