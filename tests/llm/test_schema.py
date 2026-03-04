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

"""Tests for Message serialization, especially FastAPI compatibility (issue #347)."""

import json

import pytest
from pydantic import TypeAdapter

from qwen_agent.llm.schema import ContentItem, FunctionCall, Message


class TestMessageModelDump:
    """model_dump() should exclude None fields by default."""

    def test_basic_message_excludes_none(self):
        msg = Message(role='user', content='hello')
        dump = msg.model_dump()
        assert dump == {'role': 'user', 'content': 'hello'}
        assert 'name' not in dump
        assert 'function_call' not in dump
        assert 'extra' not in dump

    def test_message_with_function_call(self):
        fc = FunctionCall(name='search', arguments='{"q": "test"}')
        msg = Message(role='assistant', content='', function_call=fc)
        dump = msg.model_dump()
        assert dump == {
            'role': 'assistant',
            'content': '',
            'function_call': {
                'name': 'search',
                'arguments': '{"q": "test"}',
            },
        }
        assert 'name' not in dump
        assert 'extra' not in dump

    def test_message_with_content_items(self):
        msg = Message(role='user', content=[ContentItem(text='hello')])
        dump = msg.model_dump()
        assert dump['content'] == [{'text': 'hello'}]

    def test_model_dump_json_excludes_none(self):
        msg = Message(role='user', content='hello')
        dump_json = msg.model_dump_json()
        assert 'null' not in dump_json
        parsed = json.loads(dump_json)
        assert parsed == {'role': 'user', 'content': 'hello'}


class TestContentItemModelDump:
    """ContentItem.model_dump() should return exactly one field."""

    def test_text_item(self):
        ci = ContentItem(text='hello')
        assert ci.model_dump() == {'text': 'hello'}

    def test_image_item(self):
        ci = ContentItem(image='http://example.com/img.png')
        assert ci.model_dump() == {'image': 'http://example.com/img.png'}

    def test_get_type_and_value(self):
        ci = ContentItem(text='hello')
        t, v = ci.get_type_and_value()
        assert t == 'text'
        assert v == 'hello'


class TestFastAPICompatibility:
    """Pydantic TypeAdapter (used by FastAPI) should also exclude None fields.

    This is the core fix for issue #347: FastAPI uses TypeAdapter internally
    for response serialization, which bypasses custom model_dump() overrides.
    """

    def test_type_adapter_dump_python_excludes_none(self):
        msg = Message(role='user', content='hello')
        ta = TypeAdapter(Message)
        dump = ta.dump_python(msg)
        assert 'name' not in dump
        assert 'function_call' not in dump
        assert 'extra' not in dump

    def test_type_adapter_dump_json_excludes_none(self):
        msg = Message(role='user', content='hello')
        ta = TypeAdapter(Message)
        dump = ta.dump_json(msg)
        assert b'null' not in dump

    def test_type_adapter_nested_excludes_none(self):
        msg = Message(
            role='assistant',
            content=[ContentItem(text='hi')],
            function_call=FunctionCall(name='test', arguments='{}'),
        )
        ta = TypeAdapter(Message)
        dump = ta.dump_python(msg)
        assert 'name' not in dump
        assert 'extra' not in dump
        assert dump['content'] == [{'text': 'hi'}]
        assert dump['function_call'] == {'name': 'test', 'arguments': '{}'}


class TestDictLikeAccess:
    """BaseModelCompatibleDict dict-like interface should still work."""

    def test_getitem(self):
        msg = Message(role='user', content='hello')
        assert msg['role'] == 'user'
        assert msg['content'] == 'hello'

    def test_setitem(self):
        msg = Message(role='user', content='hello')
        msg['name'] = 'tester'
        dump = msg.model_dump()
        assert dump['name'] == 'tester'

    def test_get_with_default(self):
        msg = Message(role='user', content='hello')
        assert msg.get('name') is None
        assert msg.get('name', 'default') == 'default'
        assert msg.get('role') == 'user'
