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

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(__file__, '../../..')))  # noqa

from examples.assistant_rag_with_citations import build_demo_knowledge, test, verify_citations  # noqa


def test_rag_citation_gate():
    # The example's own offline assertions (supported/fabricated/misattributed/frankenquote).
    test()


def test_supported_citation_passes():
    knowledge = build_demo_knowledge()
    src = knowledge[0]['source']
    verdicts = verify_citations(
        [{
            'claim': 'Denavimab cut the annual relapse rate.',
            'source': src,
            'quote': 'Denavimab reduced the annual relapse rate by 41% versus placebo',
        }],
        knowledge,
    )
    assert verdicts[0]['status'] == 'supported'
