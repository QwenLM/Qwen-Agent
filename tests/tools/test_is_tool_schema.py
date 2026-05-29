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
Tests for is_tool_schema() and BaseTool parameter validation.

Bug: is_tool_schema() required parameters to have EXACTLY the keys
{'type', 'properties', 'required'}.  Any additional key — including
'additionalProperties', 'title', '$defs' — caused the function to return
False, triggering a misleading ValueError in BaseTool.__init__() even for
schemas that are valid per the OpenAI tool-calling spec and JSON Schema.

Pydantic's model_json_schema() routinely emits 'title' and
'additionalProperties' fields, so this bug breaks the common pattern of
deriving tool parameters from a Pydantic model.
"""

import pytest

from qwen_agent.tools.base import BaseTool, is_tool_schema, register_tool

# ---------------------------------------------------------------------------
# is_tool_schema() unit tests
# ---------------------------------------------------------------------------


def _make_tool(params: dict) -> dict:
    return {'name': 'my_tool', 'description': 'A tool', 'parameters': params}


class TestIsToolSchemaExtraKeys:

    def test_minimal_schema_is_valid(self):
        """Baseline: the three required keys alone must be accepted."""
        schema = _make_tool({
            'type': 'object',
            'properties': {'x': {'type': 'string'}},
            'required': ['x'],
        })
        assert is_tool_schema(schema) is True

    def test_schema_with_additional_properties_false(self):
        """'additionalProperties' is a standard JSON Schema keyword; must be accepted."""
        schema = _make_tool({
            'type': 'object',
            'properties': {'x': {'type': 'string'}},
            'required': ['x'],
            'additionalProperties': False,
        })
        assert is_tool_schema(schema) is True

    def test_schema_with_title(self):
        """'title' is emitted by Pydantic model_json_schema(); must be accepted."""
        schema = _make_tool({
            'type': 'object',
            'properties': {'x': {'type': 'string', 'title': 'X'}},
            'required': ['x'],
            'title': 'MyInput',
        })
        assert is_tool_schema(schema) is True

    def test_schema_with_title_and_additional_properties(self):
        """Both extra keys together — the typical Pydantic output — must be accepted."""
        schema = _make_tool({
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'title': 'Query'},
                'max_results': {'type': 'integer', 'default': 10, 'title': 'Max Results'},
            },
            'required': ['query'],
            'title': 'SearchInput',
            'additionalProperties': False,
        })
        assert is_tool_schema(schema) is True

    def test_schema_missing_required_key_is_invalid(self):
        """A schema missing 'required' must still be rejected."""
        schema = _make_tool({
            'type': 'object',
            'properties': {'x': {'type': 'string'}},
            # 'required' intentionally omitted
        })
        assert is_tool_schema(schema) is False

    def test_schema_missing_properties_key_is_invalid(self):
        """A schema missing 'properties' must still be rejected."""
        schema = _make_tool({
            'type': 'object',
            'required': [],
        })
        assert is_tool_schema(schema) is False

    def test_empty_required_is_valid(self):
        """An empty 'required' list with 'additionalProperties' must be accepted."""
        schema = _make_tool({
            'type': 'object',
            'properties': {},
            'required': [],
            'additionalProperties': False,
        })
        assert is_tool_schema(schema) is True


# ---------------------------------------------------------------------------
# BaseTool integration: pydantic-style dict parameters must not raise
# ---------------------------------------------------------------------------


class TestBaseToolWithExtraSchemaKeys:

    def test_basetool_with_additionalproperties(self):
        """BaseTool must accept parameters dict containing 'additionalProperties'."""

        class _Tool(BaseTool):
            name = '_test_tool_addl'
            description = 'test'
            parameters = {
                'type': 'object',
                'properties': {'q': {'type': 'string'}},
                'required': ['q'],
                'additionalProperties': False,
            }

            def call(self, params, **kwargs):
                pass

        # Should not raise ValueError
        tool = _Tool()
        assert tool.name == '_test_tool_addl'

    def test_basetool_with_title_and_additionalproperties(self):
        """BaseTool must accept a typical Pydantic-generated parameters dict."""

        class _Tool2(BaseTool):
            name = '_test_tool_pydantic'
            description = 'test pydantic style'
            parameters = {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string', 'title': 'Query'},
                    'limit': {'type': 'integer', 'title': 'Limit', 'default': 10},
                },
                'required': ['query'],
                'title': 'SearchParams',
                'additionalProperties': False,
            }

            def call(self, params, **kwargs):
                pass

        tool = _Tool2()
        assert tool.name == '_test_tool_pydantic'
