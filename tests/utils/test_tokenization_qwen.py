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

from qwen_agent.utils.tokenization_qwen import tokenizer

TEXT = ('Transformer uses attention only. ' * 12).strip()


def test_truncate_with_non_positive_budget_returns_empty_string():
    # A non-positive budget cannot hold any token, so the result must be empty
    # instead of "all tokens except the last |max_token| ones".
    for max_token in (0, -1, -7):
        assert tokenizer.truncate(TEXT, max_token=max_token) == ''
        assert tokenizer.truncate(TEXT, max_token=max_token, keep_both_sides=True) == ''


def test_truncate_with_positive_budget_still_limits_tokens():
    for max_token in (1, 5, 20):
        truncated = tokenizer.truncate(TEXT, max_token=max_token)
        assert 0 < tokenizer.count_tokens(truncated) <= max_token

    both_sides = tokenizer.truncate(TEXT, max_token=20, keep_both_sides=True)
    assert tokenizer.count_tokens(both_sides) <= 20
    assert '...' in both_sides


if __name__ == '__main__':
    test_truncate_with_non_positive_budget_returns_empty_string()
    test_truncate_with_positive_budget_still_limits_tokens()
