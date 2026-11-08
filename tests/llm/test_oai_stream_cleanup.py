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
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import openai
import pytest

from qwen_agent.llm.base import ModelServiceError
from qwen_agent.llm.oai import TextChatAtOAI
from qwen_agent.llm.schema import Message

pytestmark = pytest.mark.skipif(openai.__version__.startswith('0.'), reason='Requires the native OpenAI v1+ client')


@pytest.fixture
def local_stream():
    servers = []

    def start(complete=False, status=200):
        state = {'observed': threading.Event()}

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(status)
                if status != 200:
                    body = json.dumps({'error': {'message': 'fixture authentication error', 'type': 'invalid_api_key'}})
                    body = body.encode()
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    self.close_connection = True
                    return
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Transfer-Encoding', 'chunked')
                self.end_headers()
                chunk = {
                    'id': 'chatcmpl-local',
                    'object': 'chat.completion.chunk',
                    'created': 0,
                    'model': 'loopback-fixture',
                    'choices': [{
                        'index': 0,
                        'delta': {
                            'content': 'hello'
                        },
                        'finish_reason': None
                    }],
                }

                def send_event(data):
                    body = ('data: ' + data + '\n\n').encode()
                    self.wfile.write(f'{len(body):x}\r\n'.encode() + body + b'\r\n')
                    self.wfile.flush()

                send_event(json.dumps(chunk))
                if complete:
                    send_event('[DONE]')
                    self.wfile.write(b'0\r\n\r\n')
                    self.wfile.flush()
                    state['peer_closed'] = None
                else:
                    self.connection.settimeout(1)
                    try:
                        state['peer_closed'] = self.connection.recv(1) == b''
                    except (ConnectionResetError, ConnectionAbortedError):
                        state['peer_closed'] = True
                    except socket.timeout:
                        state['peer_closed'] = False
                state['observed'].set()
                self.close_connection = True

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        client = openai.OpenAI(api_key='local-fixture',
                               base_url=f'http://127.0.0.1:{server.server_port}/v1',
                               max_retries=0,
                               timeout=3,
                               http_client=openai.DefaultHttpxClient(trust_env=False))
        streams = []
        model = TextChatAtOAI({
            'model': 'loopback-fixture',
            'generate_cfg': {
                'use_raw_api': True,
                'max_input_tokens': 0
            }
        })

        def create(**kwargs):
            stream = client.chat.completions.create(**kwargs)
            # Retain the real SDK stream to inspect it before fixture cleanup/GC.
            streams.append(stream)
            return stream

        model._chat_complete_create = create
        servers.append((server, thread, client, streams))
        return model, streams, state

    yield start
    for server, thread, client, streams in servers:
        for stream in streams:
            stream.close()
        client.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize('delta_stream', [False, True])
@pytest.mark.parametrize('action', ['close', 'throw', 'exhaust'])
def test_oai_stream_cleanup(local_stream, delta_stream, action):
    model, streams, state = local_stream(complete=action == 'exhaust')
    messages = [Message('user', 'local fixture')]
    if delta_stream:
        response = model._chat_stream(messages, delta_stream=True, generate_cfg={})
    else:
        response = model.chat(messages, stream=True)
    try:
        assert next(response)[0].content == 'hello'
        if action == 'close':
            response.close()
        elif action == 'throw':
            with pytest.raises(ValueError, match='consumer stopped'):
                response.throw(ValueError('consumer stopped'))
        else:
            assert list(response) == []
        assert len(streams) == 1
        # Inspect both the native response and the actual TCP peer before cleanup.
        closed = streams[0].response.is_closed
        assert state['observed'].wait(2)
        assert closed, (action, state['peer_closed'])
        if action != 'exhaust':
            assert state['peer_closed']
    finally:
        response.close()


def test_oai_stream_creation_error(local_stream):
    model, streams, _ = local_stream(status=401)
    response = model.chat([Message('user', 'local fixture')], stream=True)
    with pytest.raises(ModelServiceError) as exc:
        next(response)
    assert isinstance(exc.value.exception, openai.AuthenticationError)
    assert streams == []
