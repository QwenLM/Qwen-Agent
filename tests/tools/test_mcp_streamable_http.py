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

import asyncio
import datetime
import sys
import types
from contextlib import asynccontextmanager
from types import SimpleNamespace

from qwen_agent.tools.mcp_manager import MCPClient

STREAMABLE_HTTP_SERVER = {
    'type': 'streamable-http',
    'url': 'http://127.0.0.1:8000/mcp',
    'headers': {
        'Authorization': 'Bearer test-token'
    },
    'sse_read_timeout': 120,
}


class FakeClientSession:
    """Stand-in for mcp.ClientSession used by MCPClient.connection_server."""

    def __init__(self, read_stream, write_stream):
        self.read_stream = read_stream
        self.write_stream = write_stream

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def initialize(self):
        return None

    async def list_tools(self):
        return SimpleNamespace(tools=['dummy-tool'])

    async def list_resources(self):
        return SimpleNamespace(resources=[])


class FakeAsyncClient:
    instances = []

    def __init__(self, headers=None, timeout=None, follow_redirects=None, **kwargs):
        self.headers = headers
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.kwargs = kwargs
        FakeAsyncClient.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeTimeout:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.read = kwargs.get('read', args[0] if args else None)


def _install_module(name, module, installed):
    prev = sys.modules.get(name, None)
    installed.append((name, prev))
    sys.modules[name] = module


def _restore_modules(installed):
    for name, prev in reversed(installed):
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev


def _make_pkg(name):
    mod = types.ModuleType(name)
    mod.__path__ = []
    return mod


def _install_mcp_layout(installed, streamable_mod):
    mcp_mod = _make_pkg('mcp')
    mcp_mod.ClientSession = FakeClientSession
    mcp_mod.StdioServerParameters = object
    client_mod = _make_pkg('mcp.client')
    sse_mod = types.ModuleType('mcp.client.sse')
    sse_mod.sse_client = object
    stdio_mod = types.ModuleType('mcp.client.stdio')
    stdio_mod.stdio_client = object

    mcp_mod.client = client_mod
    client_mod.sse = sse_mod
    client_mod.stdio = stdio_mod
    client_mod.streamable_http = streamable_mod

    _install_module('mcp', mcp_mod, installed)
    _install_module('mcp.client', client_mod, installed)
    _install_module('mcp.client.sse', sse_mod, installed)
    _install_module('mcp.client.stdio', stdio_mod, installed)
    _install_module('mcp.client.streamable_http', streamable_mod, installed)
    return mcp_mod


def _install_fake_httpx2(installed):
    FakeAsyncClient.instances = []
    httpx2_mod = types.ModuleType('httpx2')
    httpx2_mod.AsyncClient = FakeAsyncClient
    httpx2_mod.Timeout = FakeTimeout
    _install_module('httpx2', httpx2_mod, installed)
    return httpx2_mod


def _connect(server=None):
    client = MCPClient()
    asyncio.run(client.connection_server('streamable-mcp-server', server or STREAMABLE_HTTP_SERVER))
    return client


def test_mcp_v2_streamablehttp_client_import_and_2_tuple_unpack():
    """mcp>=2.0: streamable_http_client + http_client, unpack a 2-tuple."""
    installed = []
    calls = []
    try:
        streamable_mod = types.ModuleType('mcp.client.streamable_http')

        @asynccontextmanager
        async def streamable_http_client(url, *, http_client=None, terminate_on_close=True):
            calls.append({
                'url': url,
                'http_client': http_client,
                'terminate_on_close': terminate_on_close,
            })
            yield ('read-stream', 'write-stream')

        streamable_mod.streamable_http_client = streamable_http_client
        _install_mcp_layout(installed, streamable_mod)
        _install_fake_httpx2(installed)

        client = _connect()

        assert calls, 'streamable_http_client was not used'
        assert calls[0]['url'] == STREAMABLE_HTTP_SERVER['url']
        http_client = calls[0]['http_client']
        assert http_client is not None
        assert http_client.headers == STREAMABLE_HTTP_SERVER['headers']
        assert http_client.follow_redirects is True
        assert http_client.timeout is not None
        assert http_client.timeout.read == float(STREAMABLE_HTTP_SERVER['sse_read_timeout'])
        assert client.session.read_stream == 'read-stream'
        assert client.session.write_stream == 'write-stream'
        assert client.tools == ['dummy-tool']
        asyncio.run(client.cleanup())
    finally:
        _restore_modules(installed)


def test_streamable_http_2_tuple_unpack_without_get_session_id():
    """Accept (read, write) when the third get_session_id callback is gone."""
    installed = []
    try:
        streamable_mod = types.ModuleType('mcp.client.streamable_http')

        @asynccontextmanager
        async def streamablehttp_client(url, headers=None, sse_read_timeout=None, **kwargs):
            yield ('read-stream', 'write-stream')

        streamable_mod.streamablehttp_client = streamablehttp_client
        _install_mcp_layout(installed, streamable_mod)

        client = _connect()
        assert client.session.read_stream == 'read-stream'
        assert client.session.write_stream == 'write-stream'
        asyncio.run(client.cleanup())
    finally:
        _restore_modules(installed)


def test_mcp_v2_rejects_legacy_headers_kwargs():
    """MCP 2 streamable_http_client only accepts url/http_client/terminate_on_close."""
    installed = []
    try:
        streamable_mod = types.ModuleType('mcp.client.streamable_http')

        @asynccontextmanager
        async def streamable_http_client(url, *, http_client=None, terminate_on_close=True):
            yield ('read-stream', 'write-stream')

        streamable_mod.streamable_http_client = streamable_http_client
        _install_mcp_layout(installed, streamable_mod)
        _install_fake_httpx2(installed)

        client = _connect()
        assert client.session.read_stream == 'read-stream'
        asyncio.run(client.cleanup())
    finally:
        _restore_modules(installed)


def test_mcp_v1_streamablehttp_client_headers_and_3_tuple():
    """extras_require still allows mcp 1.x: headers/sse_read_timeout and a 3-tuple."""
    installed = []
    calls = []
    try:
        streamable_mod = types.ModuleType('mcp.client.streamable_http')

        @asynccontextmanager
        async def streamablehttp_client(url, headers=None, sse_read_timeout=None, **kwargs):
            calls.append({
                'url': url,
                'headers': headers,
                'sse_read_timeout': sse_read_timeout,
            })
            yield ('read-stream', 'write-stream', lambda: 'session-id')

        streamable_mod.streamablehttp_client = streamablehttp_client
        _install_mcp_layout(installed, streamable_mod)

        client = _connect()

        assert len(calls) == 1
        assert calls[0]['url'] == STREAMABLE_HTTP_SERVER['url']
        assert calls[0]['headers'] == STREAMABLE_HTTP_SERVER['headers']
        assert calls[0]['sse_read_timeout'] == datetime.timedelta(seconds=STREAMABLE_HTTP_SERVER['sse_read_timeout'])
        assert client.session.read_stream == 'read-stream'
        assert client.session.write_stream == 'write-stream'
        assert client.tools == ['dummy-tool']
        asyncio.run(client.cleanup())
    finally:
        _restore_modules(installed)


def test_mcp_v1_prefers_legacy_name_when_both_exist():
    """Late mcp 1.x ships both names; keep the headers/3-tuple path."""
    installed = []
    legacy_calls = []
    v2_calls = []
    try:
        streamable_mod = types.ModuleType('mcp.client.streamable_http')

        @asynccontextmanager
        async def streamablehttp_client(url, headers=None, sse_read_timeout=None, **kwargs):
            legacy_calls.append(url)
            yield ('read-stream', 'write-stream', lambda: 'session-id')

        @asynccontextmanager
        async def streamable_http_client(url, *, http_client=None, terminate_on_close=True):
            v2_calls.append(url)
            yield ('read-stream', 'write-stream')

        streamable_mod.streamablehttp_client = streamablehttp_client
        streamable_mod.streamable_http_client = streamable_http_client
        _install_mcp_layout(installed, streamable_mod)

        client = _connect()
        assert legacy_calls == [STREAMABLE_HTTP_SERVER['url']]
        assert v2_calls == []
        assert client.session.read_stream == 'read-stream'
        asyncio.run(client.cleanup())
    finally:
        _restore_modules(installed)
