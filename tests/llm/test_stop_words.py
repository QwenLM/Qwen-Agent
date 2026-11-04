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

from qwen_agent.llm.base import _truncate_at_stop_word


def test_truncate_uses_earliest_stop_word_regardless_of_order():
    """Stop-word truncation must not depend on the order of the stop list.

    Truncating at each stop word in turn cut off the evidence of an earlier
    stop word, so text between the earliest stop word and the one that was
    matched first leaked into the output.
    """
    text = 'The FINAL END is here, END of story'

    # The earliest stop word is 'FINAL END' at index 4; every order must cut there.
    truncated, result = _truncate_at_stop_word(text, ['END', 'FINAL END'])
    assert truncated is True
    assert result == 'The '

    truncated, result = _truncate_at_stop_word(text, ['FINAL END', 'END'])
    assert truncated is True
    assert result == 'The '

    truncated, result = _truncate_at_stop_word(text, ['END', 'FINAL END', 'story'])
    assert truncated is True
    assert result == 'The '


def test_truncate_at_first_occurrence_within_one_stop_word():
    """A single stop word cuts at its first occurrence."""
    truncated, result = _truncate_at_stop_word('a END b END c', ['END'])
    assert truncated is True
    assert result == 'a '

    truncated, result = _truncate_at_stop_word('no stop word here', ['END'])
    assert truncated is False
    assert result == 'no stop word here'


def test_truncate_shorter_later_match_before_longer_earlier_match():
    """A later-listed stop word matching earlier wins over an earlier-listed one."""
    # 'ab' starts at index 1, 'b' at index 2: the earliest is 'ab'.
    truncated, result = _truncate_at_stop_word('xab', ['b', 'ab'])
    assert truncated is True
    assert result == 'x'

    truncated, result = _truncate_at_stop_word('xab', ['ab', 'b'])
    assert truncated is True
    assert result == 'x'
