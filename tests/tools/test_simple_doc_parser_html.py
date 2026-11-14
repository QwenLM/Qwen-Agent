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

from qwen_agent.tools.simple_doc_parser import parse_html_bs


def test_parse_html_bs_keeps_block_boundaries(tmp_path):
    html = ('<html><head><title>Page</title></head><body>'
            '<p>Hello</p><p>World</p>'
            '<div>Alpha</div><div>Beta</div>'
            '<ul><li>one</li><li>two</li></ul>'
            '<p>inline <b>bold</b> tail</p>'
            '</body></html>')
    html_file = tmp_path / 'page.html'
    html_file.write_text(html, encoding='utf-8')

    page = parse_html_bs(str(html_file))[0]
    paragraphs = [item['text'] for item in page['content']]

    # The title is still reported separately.
    assert page['title'] == 'Page'

    # The text of two adjacent block-level elements must not be glued together.
    assert 'Hello' in paragraphs
    assert 'World' in paragraphs
    assert not any('HelloWorld' in item for item in paragraphs)
    assert 'Alpha' in paragraphs
    assert 'one' in paragraphs

    # Inline markup must not introduce new paragraphs.
    assert any(item.strip() == 'inline bold tail' for item in paragraphs)


if __name__ == '__main__':
    import tempfile
    from pathlib import Path
    test_parse_html_bs_keeps_block_boundaries(Path(tempfile.mkdtemp()))
