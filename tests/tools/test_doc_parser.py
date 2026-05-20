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
import tempfile

from qwen_agent.tools import DocParser


def test_doc_parser():
    tool = DocParser()
    res = tool.call({'url': 'https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf'})
    print(res)


def _write_small_doc(directory: str) -> str:
    path = os.path.join(directory, 'small.txt')
    with open(path, 'w') as f:
        f.write('Qwen-Agent is a framework for developing LLM applications.\n' * 5)
    return path


def _count_extractor_calls(tool: DocParser) -> dict:
    counter = {'n': 0}
    original = tool.doc_extractor.call

    def wrapped(*args, **kwargs):
        counter['n'] += 1
        return original(*args, **kwargs)

    tool.doc_extractor.call = wrapped
    return counter


def test_doc_parser_cache_hit_for_small_doc():
    """A document small enough to skip chunking must still be served from the
    DocParser-level cache on a second call (it used to be written under a key
    that the read path never checked)."""
    with tempfile.TemporaryDirectory() as tmp:
        doc_path = _write_small_doc(tmp)
        tool = DocParser({'path': os.path.join(tmp, 'doc_parser_cache')})
        counter = _count_extractor_calls(tool)

        first = tool.call({'url': doc_path})
        second = tool.call({'url': doc_path})

        # The whole-doc record is small, so the second call must hit the cache
        # instead of re-running document extraction.
        extractions = counter['n']
        assert extractions == 1, f'expected 1 extraction, got {extractions}'
        assert first == second


def test_doc_parser_cache_not_stale_on_max_ref_token_change():
    """The whole-doc cache is keyed by max_ref_token, the value that decides
    the un-chunked branch. Lowering max_ref_token must not serve a stale
    whole-doc record that should now be chunked."""
    with tempfile.TemporaryDirectory() as tmp:
        doc_path = _write_small_doc(tmp)
        tool = DocParser({'path': os.path.join(tmp, 'doc_parser_cache')})
        counter = _count_extractor_calls(tool)

        # Large max_ref_token -> whole-doc branch, cached.
        tool.call({'url': doc_path}, max_ref_token=20000)
        assert counter['n'] == 1

        # A much smaller max_ref_token must not reuse the whole-doc record.
        tool.call({'url': doc_path}, max_ref_token=1)
        assert counter['n'] == 2, 'stale whole-doc record served after max_ref_token changed'


if __name__ == '__main__':
    test_doc_parser()
    test_doc_parser_cache_hit_for_small_doc()
    test_doc_parser_cache_not_stale_on_max_ref_token_change()
