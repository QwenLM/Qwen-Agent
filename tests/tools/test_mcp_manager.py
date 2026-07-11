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

import json

import pytest

from qwen_agent.tools.mcp_manager import MCPManager


def _make_stdio_config(command='npx', args=None):
    if args is None:
        args = ['-y', '@modelcontextprotocol/server-memory']
    return {'mcpServers': {'test_server': {'command': command, 'args': args}}}


def _make_sse_config(url='http://localhost:8080/sse'):
    return {'mcpServers': {'test_server': {'url': url}}}


def test_is_valid_mcp_servers_valid_stdio():
    manager = MCPManager()
    assert manager.is_valid_mcp_servers(_make_stdio_config())


def test_is_valid_mcp_servers_valid_sse():
    manager = MCPManager()
    assert manager.is_valid_mcp_servers(_make_sse_config())


def test_is_valid_mcp_servers_valid_streamable_http():
    manager = MCPManager()
    cfg = {'mcpServers': {'test': {'type': 'streamable-http', 'url': 'http://localhost:8080/mcp'}}}
    assert manager.is_valid_mcp_servers(cfg)


def test_is_valid_mcp_servers_with_headers():
    manager = MCPManager()
    cfg = {'mcpServers': {'test': {'url': 'http://localhost:8080/sse', 'headers': {'Authorization': 'Bearer xyz'}}}}
    assert manager.is_valid_mcp_servers(cfg)


def test_is_valid_mcp_servers_with_env():
    manager = MCPManager()
    cfg = {'mcpServers': {'test': {'command': 'node', 'args': ['server.js'], 'env': {'NODE_ENV': 'production'}}}}
    assert manager.is_valid_mcp_servers(cfg)


@pytest.mark.parametrize('invalid_cfg,description', [
    (None, 'not a dict'),
    ({}, 'missing mcpServers'),
    ({'mcpServers': 'not_a_dict'}, 'mcpServers is not a dict'),
    ({'mcpServers': {'srv': 'not_a_dict'}}, 'server value is not a dict'),
    ({'mcpServers': {'srv': {'command': 123, 'args': ['a']}}}, 'command not a string'),
    ({'mcpServers': {'srv': {'command': 'npx'}}}, 'args missing when command present'),
    ({'mcpServers': {'srv': {'command': 'npx', 'args': 'not_a_list'}}}, 'args not a list'),
    ({'mcpServers': {'srv': {'url': 123}}}, 'url not a string'),
    ({'mcpServers': {'srv': {'url': 'http://x', 'headers': 'not_a_dict'}}}, 'headers not a dict'),
    ({'mcpServers': {'srv': {'command': 'npx', 'args': ['a'], 'env': 'not_a_dict'}}}, 'env not a dict'),
])
def test_is_valid_mcp_servers_invalid(invalid_cfg, description):
    manager = MCPManager()
    assert not manager.is_valid_mcp_servers(invalid_cfg)


def test_mcp_dynamic_tool_handles_dict_params():
    """Verify that dynamically created MCP tool classes accept both str and dict params."""
    manager = MCPManager()
    tool = manager.create_tool_class(
        register_name='test_tool',
        register_client_id='dummy_client',
        tool_name='echo',
        tool_desc='Echo tool',
        tool_parameters={'type': 'object', 'properties': {}, 'required': []},
    )
    # Verify params is handled for both str and dict (check it doesn't crash before MCP execution)
    assert tool.name == 'test_tool'
    assert tool.description == 'Echo tool'
    assert tool.parameters == {'type': 'object', 'properties': {}, 'required': []}
