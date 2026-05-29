# Copyright 2024 The Qwen team, Alibaba Group. All rights reserved.
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

"""
Tests for BaseModelCompatibleDict.get() with falsy-but-valid values.

Bug: get() used truthiness check (`if value:`) instead of None check
(`if value is not None:`), so falsy values like empty string "", empty list [],
0, and False were incorrectly replaced by the caller-supplied default.
"""

import pytest

from qwen_agent.llm.schema import ContentItem, FunctionCall, Message


class TestBaseModelCompatibleDictGet:

    def test_get_empty_string_content_returns_empty_string(self):
        """An empty string content is a valid value and must not be replaced by default."""
        msg = Message(role='user', content='')
        assert msg.get('content', 'MISSING') == ''

    def test_get_non_empty_string_content(self):
        """Normal non-empty content should be returned as-is."""
        msg = Message(role='user', content='hello')
        assert msg.get('content', 'MISSING') == 'hello'

    def test_get_none_field_returns_default(self):
        """A field that is None should return the caller-supplied default."""
        msg = Message(role='assistant', content='hi')
        # reasoning_content defaults to None
        assert msg.get('reasoning_content', 'DEFAULT') == 'DEFAULT'

    def test_get_none_field_returns_none_when_no_default(self):
        """A field that is None and no default supplied returns None."""
        msg = Message(role='assistant', content='hi')
        assert msg.get('reasoning_content') is None

    def test_get_empty_list_content_returns_empty_list(self):
        """An empty list content is a valid value and must not be replaced by default."""
        msg = Message(role='user', content=[])
        # content=[] is falsy but valid; default must not apply
        assert msg.get('content', 'MISSING') == []

    def test_get_existing_string_role(self):
        """Role field (always a non-empty string) should be returned normally."""
        msg = Message(role='user', content='test')
        assert msg.get('role', 'MISSING') == 'user'

    def test_get_missing_attribute_returns_default(self):
        """Non-existent attribute should return the caller-supplied default."""
        msg = Message(role='user', content='test')
        assert msg.get('nonexistent_field', 'DEFAULT') == 'DEFAULT'

    def test_get_on_function_call_with_empty_arguments(self):
        """FunctionCall.arguments='' is falsy but valid."""
        fc = FunctionCall(name='my_fn', arguments='')
        assert fc.get('arguments', 'MISSING') == ''

    def test_get_on_content_item_with_empty_text(self):
        """ContentItem.text='' is falsy but valid."""
        item = ContentItem(text='')
        assert item.get('text', 'MISSING') == ''
