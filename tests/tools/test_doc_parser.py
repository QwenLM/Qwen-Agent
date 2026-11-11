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

from qwen_agent.tools import DocParser


def test_doc_parser():
    tool = DocParser()
    res = tool.call({'url': 'https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf'})
    print(res)


def test_call_reads_the_chunked_document_from_cache(tmp_path):
    # A small document is cached under '<hash>_without_chunking' but was looked
    # up under '<hash>_<page_size>', so every call re-extracted and re-chunked.
    class CountingExtractor:

        def __init__(self):
            self.calls = 0

        def call(self, params):
            self.calls += 1
            return [{'page_num': 1, 'content': [{'text': 'hello world', 'token': 2}]}]

    tool = DocParser({'path': str(tmp_path)})
    tool.doc_extractor = CountingExtractor()

    first = tool.call({'url': 'file:///tmp/small.txt'})
    second = tool.call({'url': 'file:///tmp/small.txt'})

    assert tool.doc_extractor.calls == 1
    assert first == second


if __name__ == '__main__':
    test_doc_parser()
