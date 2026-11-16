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

from qwen_agent.agents.write_from_scratch import is_roman_numeral


def test_roman_numeral_headings_are_detected():
    for heading in ['I. Introduction', 'III. Methods', 'IV) Results', 'II、资料', 'V']:
        assert is_roman_numeral(heading), heading


def test_ordinary_text_is_not_treated_as_a_heading():
    # These lines only start with a roman numeral letter, they are not numbered headings.
    for text in [
            'Introduction', 'In this section', 'Marketing overview', 'Methods and data', 'Various topics', 'Details',
            'Critical analysis', 'Conclusion'
    ]:
        assert not is_roman_numeral(text), text


if __name__ == '__main__':
    test_roman_numeral_headings_are_detected()
    test_ordinary_text_is_not_treated_as_a_heading()
