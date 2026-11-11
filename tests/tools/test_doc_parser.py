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


def test_split_doc_to_chunk_keeps_sentence_punctuation():
    # A long paragraph is split at sentence boundaries; the delimiters used to
    # be discarded, so every chunk lost the '。' / '. ' that ended its sentences.
    tool = DocParser({'path': '/tmp/doc_parser_test'})
    doc = [{'page_num': 1, 'content': [{'text': '第一句很重要。第二句也很重要。', 'token': 999}]}]

    chunks = tool.split_doc_to_chunk(doc, 'x.txt', parser_page_size=10)

    assert len(chunks) > 0
    joined = ''.join(c.content for c in chunks)
    assert '第一句很重要。' in joined
    assert '第二句也很重要。' in joined
    for chunk in chunks:
        assert chunk.content.rstrip().endswith('。'), chunk.content


if __name__ == '__main__':
    test_doc_parser()
