# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from qwen_agent.tools.mcp_manager import MCPClient

mcp = pytest.importorskip('mcp')


@pytest.fixture(params=[
    {
        'command': 'unused',
        'args': []
    },
    {
        'url': 'https://example.invalid/sse'
    },
    {
        'url': 'https://example.invalid/mcp',
        'type': 'streamable-http'
    },
],
                ids=['stdio', 'sse', 'streamable-http'])
def server_config(request):
    return request.param


@pytest.fixture
def session(monkeypatch):
    session = MagicMock(spec=mcp.ClientSession)
    session.list_resources = AsyncMock(return_value=mcp.types.ListResourcesResult(resources=[]))

    @asynccontextmanager
    async def client_session(*args, **kwargs):
        yield session

    @asynccontextmanager
    async def transport(*args, **kwargs):
        yield None, None

    @asynccontextmanager
    async def http_transport(*args, **kwargs):
        yield None, None, None

    monkeypatch.setattr('mcp.ClientSession', client_session)
    monkeypatch.setattr('mcp.client.stdio.stdio_client', transport)
    monkeypatch.setattr('mcp.client.sse.sse_client', transport)
    monkeypatch.setattr('mcp.client.streamable_http.streamablehttp_client', http_transport)
    return session


def tool_page(names, cursor=None):
    return mcp.types.ListToolsResult(
        tools=[mcp.types.Tool(name=name, inputSchema={'type': 'object'}) for name in names], nextCursor=cursor)


@pytest.mark.parametrize('pages, expected_names, expected_calls', [
    ([tool_page(['first'])], ['first'], [call()]),
    ([tool_page([])], [], [call()]),
    ([tool_page(['first'], 'opaque/next=='),
      tool_page([], 'last'), tool_page(['second'])], ['first', 'second'],
     [call(), call(cursor='opaque/next=='), call(cursor='last')]),
    ([tool_page([], 'page-2'), tool_page(['second'])], ['second'], [call(), call(cursor='page-2')]),
])
def test_connection_discovers_all_tool_pages(session, server_config, pages, expected_names, expected_calls):
    session.list_tools.side_effect = pages

    async def connect():
        client = MCPClient()
        try:
            await client.connection_server('paged', server_config)
            assert [tool.name for tool in client.tools] == expected_names
        finally:
            await client.cleanup()

    asyncio.run(connect())
    assert session.list_tools.await_args_list == expected_calls


def test_connection_does_not_publish_partial_tool_list(session, server_config):
    session.list_tools.side_effect = [tool_page(['first'], 'page-2'), RuntimeError('second page failed')]

    async def connect():
        client = MCPClient()
        try:
            with pytest.raises(RuntimeError, match='second page failed'):
                await client.connection_server('paged', server_config)
            assert client.tools is None
        finally:
            await client.cleanup()

    asyncio.run(connect())
