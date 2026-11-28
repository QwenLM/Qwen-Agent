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

from qwen_agent.tools import SimpleDocParser


def test_simple_doc_parser():
    tool = SimpleDocParser()
    res = tool.call({'url': 'https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf'})
    print(res)


@pytest.mark.parametrize('extension', ['csv', 'tsv', 'xlsx'])
def test_table_preserves_literal_na_values(tmp_path, extension):
    rows = [('region', 'status', 'unused'), ('NA', 'NULL', ''), ('EU', 'N/A', ''), ('NA', '', '')]
    path = tmp_path / f'regions.{extension}'
    if extension == 'xlsx':
        openpyxl = pytest.importorskip('openpyxl')
        workbook = openpyxl.Workbook()
        for row in rows:
            workbook.active.append(row)
        workbook.save(path)
    else:
        separator = ',' if extension == 'csv' else '\t'
        path.write_text('\n'.join(separator.join(row) for row in rows), encoding='utf-8')

    parser = SimpleDocParser({'path': str(tmp_path / 'cache')})
    table = parser.call({'url': str(path)})
    cells = [
        [cell.strip() for cell in line.strip('|').split('|')] for line in table.splitlines() if line.startswith('|')
    ]
    assert cells[0] == ['region', 'status']
    assert cells[2:] == [['NA', 'NULL'], ['EU', 'N/A'], ['NA', '']]


if __name__ == '__main__':
    test_simple_doc_parser()
