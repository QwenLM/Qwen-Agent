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

"""Tests for MCP schema $ref resolution (issue #752)."""

from qwen_agent.tools.mcp_manager import _resolve_schema_refs


class TestResolveSchemaRefs:

    def test_simple_ref_resolved(self):
        """A single $ref to $defs should be inlined."""
        schema = {
            'type': 'object',
            'properties': {
                'config': {'$ref': '#/$defs/ConfigModel'}
            },
            'required': ['config'],
            '$defs': {
                'ConfigModel': {
                    'type': 'object',
                    'properties': {'key': {'type': 'string'}},
                    'required': ['key']
                }
            }
        }
        defs = schema['$defs']
        result = _resolve_schema_refs(schema, defs)
        assert result['properties']['config'] == {
            'type': 'object',
            'properties': {'key': {'type': 'string'}},
            'required': ['key']
        }
        assert '$defs' not in result
        assert '$ref' not in result['properties']['config']

    def test_no_refs_unchanged(self):
        """Schema without $ref should pass through unchanged (minus $defs key)."""
        schema = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'}
            },
            'required': ['name']
        }
        result = _resolve_schema_refs(schema, {})
        assert result == schema

    def test_nested_ref_resolved(self):
        """Nested $ref (A references B which references C) should resolve recursively."""
        defs = {
            'Address': {
                'type': 'object',
                'properties': {
                    'city': {'$ref': '#/$defs/City'}
                }
            },
            'City': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'}
                }
            }
        }
        schema = {
            'type': 'object',
            'properties': {
                'address': {'$ref': '#/$defs/Address'}
            },
            '$defs': defs
        }
        result = _resolve_schema_refs(schema, defs)
        addr = result['properties']['address']
        assert addr['properties']['city'] == {
            'type': 'object',
            'properties': {'name': {'type': 'string'}}
        }

    def test_circular_ref_left_as_is(self):
        """Circular $ref should not infinite-loop; the circular ref is left as-is."""
        defs = {
            'Node': {
                'type': 'object',
                'properties': {
                    'child': {'$ref': '#/$defs/Node'}
                }
            }
        }
        schema = {
            'type': 'object',
            'properties': {
                'root': {'$ref': '#/$defs/Node'}
            },
            '$defs': defs
        }
        result = _resolve_schema_refs(schema, defs)
        # First level resolved, but the circular child ref remains
        root = result['properties']['root']
        assert root['type'] == 'object'
        assert root['properties']['child'] == {'$ref': '#/$defs/Node'}

    def test_unresolvable_ref_left_as_is(self):
        """$ref pointing to a missing definition should be left unchanged."""
        schema = {
            'type': 'object',
            'properties': {
                'x': {'$ref': '#/$defs/DoesNotExist'}
            }
        }
        result = _resolve_schema_refs(schema, {})
        assert result['properties']['x'] == {'$ref': '#/$defs/DoesNotExist'}

    def test_ref_in_array_items(self):
        """$ref inside array items should be resolved."""
        defs = {
            'Item': {
                'type': 'object',
                'properties': {'id': {'type': 'integer'}}
            }
        }
        schema = {
            'type': 'object',
            'properties': {
                'items': {
                    'type': 'array',
                    'items': {'$ref': '#/$defs/Item'}
                }
            },
            '$defs': defs
        }
        result = _resolve_schema_refs(schema, defs)
        assert result['properties']['items']['items'] == {
            'type': 'object',
            'properties': {'id': {'type': 'integer'}}
        }

    def test_definitions_key_also_stripped(self):
        """The 'definitions' key (older JSON Schema draft) should also be stripped."""
        schema = {
            'type': 'object',
            'properties': {
                'x': {'$ref': '#/definitions/Foo'}
            },
            'definitions': {
                'Foo': {'type': 'string'}
            }
        }
        defs = schema['definitions']
        result = _resolve_schema_refs(schema, defs)
        assert result['properties']['x'] == {'type': 'string'}
        assert 'definitions' not in result

    def test_ref_with_sibling_properties_merged(self):
        """Pydantic v2 places description/default alongside $ref; siblings should be merged."""
        defs = {
            'Address': {
                'type': 'object',
                'properties': {'city': {'type': 'string'}}
            }
        }
        schema = {
            'type': 'object',
            'properties': {
                'addr': {
                    '$ref': '#/$defs/Address',
                    'description': 'Home address',
                    'default': None
                }
            },
            '$defs': defs
        }
        result = _resolve_schema_refs(schema, defs)
        addr = result['properties']['addr']
        assert addr['type'] == 'object'
        assert addr['properties'] == {'city': {'type': 'string'}}
        assert addr['description'] == 'Home address'
        assert addr['default'] is None
        assert '$ref' not in addr

    def test_non_local_ref_left_as_is(self):
        """$ref with non-local path (e.g. OpenAPI #/components/...) should not be resolved."""
        defs = {'MyModel': {'type': 'string'}}
        schema = {
            'type': 'object',
            'properties': {
                'x': {'$ref': '#/components/schemas/MyModel'}
            }
        }
        result = _resolve_schema_refs(schema, defs)
        assert result['properties']['x'] == {'$ref': '#/components/schemas/MyModel'}

    def test_non_string_ref_left_as_is(self):
        """Malformed $ref (non-string) should not crash."""
        schema = {
            'type': 'object',
            'properties': {
                'x': {'$ref': 123}
            }
        }
        result = _resolve_schema_refs(schema, {})
        assert result['properties']['x'] == {'$ref': 123}

    def test_multiple_properties_share_one_def(self):
        """Two properties referencing the same $def should both resolve independently."""
        defs = {
            'Shared': {
                'type': 'object',
                'properties': {'id': {'type': 'integer'}}
            }
        }
        schema = {
            'type': 'object',
            'properties': {
                'a': {'$ref': '#/$defs/Shared'},
                'b': {'$ref': '#/$defs/Shared', 'description': 'second'}
            },
            '$defs': defs
        }
        result = _resolve_schema_refs(schema, defs)
        assert result['properties']['a']['type'] == 'object'
        assert result['properties']['b']['type'] == 'object'
        assert result['properties']['b']['description'] == 'second'

    def test_allof_with_ref_resolved(self):
        """$ref inside allOf should be resolved."""
        defs = {
            'Base': {
                'type': 'object',
                'properties': {'id': {'type': 'integer'}}
            }
        }
        schema = {
            'type': 'object',
            'properties': {
                'item': {
                    'allOf': [
                        {'$ref': '#/$defs/Base'},
                        {'properties': {'name': {'type': 'string'}}}
                    ]
                }
            },
            '$defs': defs
        }
        result = _resolve_schema_refs(schema, defs)
        allof = result['properties']['item']['allOf']
        assert allof[0] == {
            'type': 'object',
            'properties': {'id': {'type': 'integer'}}
        }
        assert allof[1] == {'properties': {'name': {'type': 'string'}}}
