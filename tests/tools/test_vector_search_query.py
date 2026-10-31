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
"""Offline query-boundary regressions for vector and vector-backed hybrid search."""

import sys
from types import ModuleType, SimpleNamespace

import pytest

from qwen_agent.tools import HybridSearch, VectorSearch
from qwen_agent.tools.doc_parser import Chunk, Record
from qwen_agent.utils.tokenization_qwen import count_tokens


@pytest.fixture
def vector_backend(monkeypatch):
    """Keep optional embedding/vector-store dependencies offline."""
    calls = []

    class Embeddings:

        def __init__(self, **kwargs):
            pass

    class VectorStore:

        @classmethod
        def from_documents(cls, documents, embeddings):
            store = cls()
            store.documents = documents
            return store

        def similarity_search_with_score(self, query, k):
            calls.append(query)
            # Embedding services require text, even if a JSON envelope is used.
            if not isinstance(query, str):
                raise TypeError('The embedding query must be a string')
            assert k == len(self.documents) == 2
            return [(self.documents[1], 0.1), (self.documents[0], 0.9)]

    for module_name, attributes in {
            'langchain.schema': {
                'Document': SimpleNamespace
            },
            'langchain_community.embeddings': {
                'DashScopeEmbeddings': Embeddings
            },
            'langchain_community.vectorstores': {
                'FAISS': VectorStore
            },
    }.items():
        module = ModuleType(module_name)
        for name, value in attributes.items():
            setattr(module, name, value)
        monkeypatch.setitem(sys.modules, module_name, module)
    monkeypatch.setenv('DASHSCOPE_API_KEY', '')
    return calls


@pytest.fixture(params=[VectorSearch, HybridSearch], ids=['vector', 'hybrid'])
def search_tool(request):
    return request.param({'rag_searchers': ['vector_search']})


@pytest.mark.parametrize('query, expected_query', [
    ('2026', '2026'),
    ('3.14', '3.14'),
    ('null', 'null'),
    ('true', 'true'),
    ('false', 'false'),
    ('["text"]', '["text"]'),
    ('"text"', '"text"'),
    ('[]', '[]'),
    ('"topic"', '"topic"'),
    ('{}', '{}'),
    ('{"text": null}', '{"text": null}'),
    ('{"text": 7}', '{"text": 7}'),
    ('{"text": ["topic"]}', '{"text": ["topic"]}'),
    ('{"text": {"nested": "topic"}}', '{"text": {"nested": "topic"}}'),
    ('{"text": "topic", "keywords_en": ["search"]}', 'topic'),
    ('{"text": ""}', ''),
    ('natural language query', 'natural language query'),
    ('{not JSON}', '{not JSON}'),
])
def test_vector_search_preserves_query_text(search_tool, vector_backend, query, expected_query):
    texts = ['Introduction without the answer.', 'Relevant evidence from the document.']
    doc = Record(url='document.txt',
                 title='Document',
                 raw=[
                     Chunk(content=text, metadata={
                         'source': 'document.txt',
                         'chunk_id': i
                     }, token=count_tokens(text)) for i, text in enumerate(texts)
                 ])
    # Force retrieval rather than the full-document shortcut, and fit one chunk.
    budget = count_tokens(texts[1])
    assert sum(chunk.token for chunk in doc.raw) > budget

    result = search_tool.call({'query': query}, docs=[doc], max_ref_token=budget)

    assert vector_backend == [expected_query]
    assert result == [{'url': 'document.txt', 'text': [texts[1]]}]
