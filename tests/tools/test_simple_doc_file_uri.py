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

from qwen_agent.tools.simple_doc_parser import SimpleDocParser


@pytest.mark.parametrize('filename', ['plain.txt', 'with space.txt', '中文.txt', 'page.html'])
@pytest.mark.parametrize('use_uri', [False, True], ids=['native-path', 'file-uri'])
def test_parse_local_text_document(tmp_path, filename, use_uri):
    source = tmp_path / filename
    content = '<html><body><p>document text</p></body></html>' if filename.endswith('.html') else 'document text'
    source.write_text(content, encoding='utf-8')
    parser = SimpleDocParser({'path': str(tmp_path / 'cache')})
    location = source.as_uri() if use_uri else str(source)

    assert parser.call({'url': location}) == 'document text'

    # Cache identity continues to use the original caller-supplied URI/path.
    source.unlink()
    assert parser.call({'url': location}) == 'document text'
