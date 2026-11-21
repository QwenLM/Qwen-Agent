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

from qwen_agent.tools.extract_doc_vocabulary import ExtractDocVocabulary
from qwen_agent.tools.simple_doc_parser import SimpleDocParser

pytest.importorskip('sklearn')


@pytest.mark.parametrize('files', [['first.txt', 'second.txt'], ['second.txt', 'first.txt']])
def test_vocabulary_scores_include_all_documents(tmp_path, monkeypatch, files):
    documents = {'first.txt': 'alpha beta', 'second.txt': 'zebra'}
    monkeypatch.setattr(SimpleDocParser, 'call', lambda self, params, **kwargs: documents[params['url']])
    tool = ExtractDocVocabulary({'path': str(tmp_path)})

    # Each document is L2-normalized: zebra scores 1, alpha and beta 1/sqrt(2).
    assert tool.call({'files': files}) == 'zebra, alpha, beta'


def test_vocabulary_single_document_ranking(tmp_path, monkeypatch):
    monkeypatch.setattr(SimpleDocParser, 'call', lambda self, params, **kwargs: 'zebra zebra alpha')
    tool = ExtractDocVocabulary({'path': str(tmp_path)})

    assert tool.call({'files': ['single.txt']}) == 'zebra, alpha'
