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

import re

from qwen_agent.tools.simple_doc_parser import parse_csv, parse_tsv


def _cell_count(line: str) -> int:
    # A '|' escaped with a backslash belongs to the cell content, not to the table markup.
    return len(re.findall(r'(?<!\\)\|', line)) - 1


def test_csv_line_break_in_cell_keeps_rows(tmp_path):
    csv_file = tmp_path / 'table.csv'
    csv_file.write_text('name,desc\nfoo,plain\nbar,"line1\nline2"\n', encoding='utf-8', newline='')

    table = parse_csv(str(csv_file))[0]['content'][0]['table']
    lines = table.split('\n')

    # header + separator + one row per record: a line break inside a cell must not add a row
    assert len(lines) == 4
    assert [_cell_count(line) for line in lines] == [2, 2, 2, 2]


def test_csv_pipe_in_cell_keeps_columns(tmp_path):
    csv_file = tmp_path / 'table.csv'
    csv_file.write_text('name,desc\nfoo,"a|b"\nbar,plain\n', encoding='utf-8', newline='')

    table = parse_csv(str(csv_file))[0]['content'][0]['table']
    lines = table.split('\n')

    # a '|' inside a cell must not add a column
    assert [_cell_count(line) for line in lines] == [2, 2, 2, 2]
    assert 'a\\|b' in table


def test_tsv_line_break_in_cell_keeps_rows(tmp_path):
    tsv_file = tmp_path / 'table.tsv'
    tsv_file.write_text('name\tdesc\nfoo\t"line1\nline2"\n', encoding='utf-8', newline='')

    table = parse_tsv(str(tsv_file))[0]['content'][0]['table']
    lines = table.split('\n')

    # header + separator + one quoted record
    assert len(lines) == 3
    assert [_cell_count(line) for line in lines] == [2, 2, 2]


if __name__ == '__main__':
    import tempfile
    from pathlib import Path
    _tmp = Path(tempfile.mkdtemp())
    test_csv_line_break_in_cell_keeps_rows(_tmp)
    test_csv_pipe_in_cell_keeps_columns(_tmp)
    test_tsv_line_break_in_cell_keeps_rows(_tmp)
