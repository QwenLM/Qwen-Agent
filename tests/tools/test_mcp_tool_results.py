import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp.types import CallToolResult, TextContent, TextResourceContents

from qwen_agent.tools.mcp_manager import MCPClient


def execute_result(response):
    client = MCPClient()
    client.session = SimpleNamespace(send_ping=AsyncMock(), call_tool=AsyncMock(return_value=response))
    result = asyncio.run(client.execute_function('get_weather', {'city': 'Hangzhou'}))
    client.session.call_tool.assert_awaited_once_with('get_weather', {'city': 'Hangzhou'})
    return result


@pytest.mark.parametrize('structured', [
    {
        'city': '\u676d\u5dde',
        'temperature': 0
    },
    {},
    {
        'items': []
    },
    {
        'success': False,
        'detail': None
    },
])
def test_structured_only_tool_result_is_not_an_execution_error(structured):
    result = execute_result(CallToolResult(content=[], structuredContent=structured))
    assert json.loads(result) == structured
    if 'city' in structured:
        assert structured['city'] in result


@pytest.mark.parametrize('structured', [None, {'temperature': 25}])
def test_text_content_keeps_precedence_over_structured_result(structured):
    response = CallToolResult(content=[TextContent(type='text', text='first'),
                                       TextContent(type='text', text='second')],
                              structuredContent=structured)
    assert execute_result(response) == 'first\n\nsecond'


def test_legacy_result_without_structured_content_is_supported():
    response = SimpleNamespace(content=[TextContent(type='text', text='legacy result')])
    assert execute_result(response) == 'legacy result'


def test_empty_legacy_result_keeps_existing_error_fallback():
    assert execute_result(SimpleNamespace(content=[])) == 'execute error'


def test_empty_text_block_keeps_existing_text_precedence():
    response = CallToolResult(content=[TextContent(type='text', text='')], structuredContent={'temperature': 25})
    assert execute_result(response) == ''


def test_empty_tool_result_keeps_existing_error_fallback():
    assert execute_result(CallToolResult(content=[])) == 'execute error'


def test_list_resources_keeps_existing_dispatch():
    client = MCPClient()
    client.session = SimpleNamespace(send_ping=AsyncMock(),
                                     list_resources=AsyncMock(return_value=SimpleNamespace(resources=[])))
    assert asyncio.run(client.execute_function('list_resources', {})) == 'No resources found'
    client.session.list_resources.assert_awaited_once_with()


def test_read_resource_keeps_existing_dispatch():
    uri = 'resource://example/note'
    response = SimpleNamespace(contents=[TextResourceContents(uri=uri, text='resource text')])
    client = MCPClient()
    client.session = SimpleNamespace(send_ping=AsyncMock(), read_resource=AsyncMock(return_value=response))
    assert asyncio.run(client.execute_function('read_resource', {'uri': uri})) == 'resource text'
    client.session.read_resource.assert_awaited_once_with(uri)
