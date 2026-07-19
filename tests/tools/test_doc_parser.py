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
from qwen_agent.utils.tokenization_qwen import count_tokens


def test_doc_parser():
    tool = DocParser()
    res = tool.call({'url': 'https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf'})
    print(res)


def test_split_doc_to_chunk_long_paragraph_small_page_size():
    # A paragraph that exactly fills the chunk budget, followed by a long paragraph
    # without sentence delimiters, used to leave available_token == 0 and raise
    # "ValueError: range() arg 3 must not be zero" while splitting the long paragraph.
    parser = DocParser()
    for page_size in [32, 64, 100, 128, 150, 256]:
        head = '中' * page_size
        body = '文' * 3000
        doc = [{
            'page_num': 0,
            'content': [
                {'text': head, 'token': count_tokens(head)},
                {'text': body, 'token': count_tokens(body)},
            ],
        }]
        chunks = parser.split_doc_to_chunk(doc, path='doc', parser_page_size=page_size)
        assert chunks, f'no chunks produced for page_size={page_size}'
        # No content should be lost while chunking.
        joined = ''.join(chunk.content for chunk in chunks)
        assert joined.count('中') >= page_size
        assert joined.count('文') >= 3000


if __name__ == '__main__':
    test_doc_parser()
