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

from qwen_agent.tools import SimpleDocParser


def test_simple_doc_parser():
    tool = SimpleDocParser()
    res = tool.call({'url': 'https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf'})
    print(res)


if __name__ == '__main__':
    test_simple_doc_parser()


def test_parse_word_preserves_nested_tables(tmp_path):
    from docx import Document
    from qwen_agent.tools.simple_doc_parser import parse_word

    doc = Document()
    doc.add_paragraph('Lesson rubric')
    outer = doc.add_table(rows=1, cols=2)
    outer.cell(0, 0).text = 'Experiment assessment'
    cell = outer.cell(0, 1)
    cell.text = 'Required steps'
    nested = cell.add_table(rows=2, cols=2)
    nested.cell(0, 0).text = 'Safety goggles'
    nested.cell(0, 1).text = '2 points'
    nested.cell(1, 0).text = 'Record observations'
    nested.cell(1, 1).text = '3 points'
    nested.cell(1, 0).add_table(rows=1, cols=1).cell(0, 0).text = 'Include temperature readings'
    cell.add_paragraph('Total: 5 points')
    path = tmp_path / 'rubric.docx'
    doc.save(path)

    parsed = parse_word(str(path))
    table = parsed[0]['content'][1]['table']
    terms = [
        'Required steps', 'Safety goggles', '2 points', 'Record observations', 'Include temperature readings',
        '3 points', 'Total: 5 points'
    ]
    positions = [table.index(term) for term in terms]
    assert positions == sorted(positions)
    assert parsed[0]['content'][0] == {'text': 'Lesson rubric'}
    assert parsed[0]['page_num'] == 1

    plain = tmp_path / 'plain.docx'
    simple = Document()
    simple.add_table(rows=1, cols=2).cell(0, 0).text = 'Ordinary cell'
    simple.save(plain)
    assert parse_word(str(plain))[0]['content'] == [{'table': '|Ordinary cell||'}]

    tool = SimpleDocParser({'path': str(tmp_path / 'cache')})
    output = tool.call({'url': str(path)})
    assert all(term in output for term in terms)
    assert tool.call({'url': str(path)}) == output
