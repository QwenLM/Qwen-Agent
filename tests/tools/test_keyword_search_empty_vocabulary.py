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

from qwen_agent.tools import KeywordSearch, Retrieval
from qwen_agent.tools.doc_parser import Chunk, Record
from qwen_agent.utils.tokenization_qwen import count_tokens, tokenizer


def make_record(texts):
    return Record(url='document.txt',
                  title='Document',
                  raw=[
                      Chunk(content=text, metadata={
                          'source': 'document.txt',
                          'chunk_id': i
                      }, token=count_tokens(text)) for i, text in enumerate(texts)
                  ])


@pytest.mark.parametrize('texts', [[], [''], [' \n\t'], ['!?;:'], ['to be or not to be'], ['', 'the and or']])
def test_sort_without_document_keywords(texts):
    assert KeywordSearch().sort_by_scores('quote', [make_record(texts)]) == []


def test_sort_without_documents():
    assert KeywordSearch().sort_by_scores('quote', []) == []


@pytest.mark.parametrize('empty_text', ['', 'the and or'])
def test_sort_with_some_empty_keyword_lists(empty_text):
    doc = make_record([empty_text, 'needle needle', 'granite basalt'])
    tool = KeywordSearch()

    scores = tool.sort_by_scores('needle', [doc])

    assert scores[0][:2] == ('document.txt', 1)
    assert scores[0][2] > 0
    assert {chunk_id for _, chunk_id, _ in scores} == {0, 1, 2}
    assert all(score == 0 for _, _, score in scores[1:])
    assert tool.call({'query': 'needle'}, docs=[doc], max_ref_token=1) == [{
        'url': 'document.txt',
        'text': [tokenizer.truncate('needle needle', max_token=1)]
    }]


@pytest.mark.parametrize('hybrid', [False, True])
def test_retrieval_without_document_keywords(tmp_path, monkeypatch, hybrid):
    monkeypatch.chdir(tmp_path)
    text = 'to be or not to be'
    files = []
    for name in ['first.txt', 'second.txt']:
        path = tmp_path / name
        path.write_text(text, encoding='utf-8')
        files.append(str(path))
    budget = count_tokens(text)
    searchers = ['keyword_search', 'front_page_search'] if hybrid else ['keyword_search']
    tool = Retrieval({'max_ref_token': budget, 'rag_searchers': searchers})

    result = tool.call({'query': 'quote', 'files': files})

    if hybrid:
        assert result == [{'url': files[0], 'text': [text]}]
    else:
        expected_text = tokenizer.truncate(text, max_token=budget // len(files))
        assert result == [{'url': path, 'text': [expected_text]} for path in files]
