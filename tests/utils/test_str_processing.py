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

from qwen_agent.utils.str_processing import rm_cid, rm_continuous_placeholders, rm_hexadecimal, rm_newlines


def test_rm_newlines():
    # Newlines between English words become spaces.
    assert rm_newlines('hello\nworld') == 'hello world'
    # Newlines between Chinese characters are removed (no space inserted).
    assert rm_newlines('你好\n世界') == '你好世界'
    # A trailing hyphenated line break joins the word.
    assert rm_newlines('exam-\n') == 'exam'
    # A newline right after a sentence terminator is kept.
    assert rm_newlines('end.\nnext') == 'end.\nnext'


def test_rm_cid():
    assert rm_cid('abc(cid:12)def') == 'abcdef'
    assert rm_cid('no cid here') == 'no cid here'


def test_rm_hexadecimal():
    # Long hexadecimal runs (>= 21 chars) are stripped.
    assert rm_hexadecimal('x' + 'a' * 25 + 'y') == 'xy'
    # Short hexadecimal strings are left untouched.
    assert rm_hexadecimal('deadbeef') == 'deadbeef'


def test_rm_continuous_placeholders():
    # A long run of placeholder characters collapses to a tab.
    assert rm_continuous_placeholders('a........b') == 'a\tb'
    # Three or more consecutive newlines collapse to two.
    assert rm_continuous_placeholders('a\n\n\n\nb') == 'a\n\nb'


if __name__ == '__main__':
    test_rm_newlines()
    test_rm_cid()
    test_rm_hexadecimal()
    test_rm_continuous_placeholders()
