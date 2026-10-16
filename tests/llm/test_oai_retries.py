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

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import openai
import pytest

from qwen_agent.llm import ModelServiceError, get_chat_model

pytestmark = pytest.mark.skipif(openai.__version__.startswith('0.'), reason='Exercises OpenAI SDK v1+ client retries')


@pytest.fixture
def endpoint(monkeypatch):
    """Count real SDK requests to a local endpoint without backoff delays."""
    state = {'requests': [], 'failures': float('inf')}

    class Handler(BaseHTTPRequestHandler):

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['requests'].append(body)
            if len(state['requests']) <= state['failures']:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": {"message": "temporarily unavailable", "type": "server_error"}}')
                return

            self.send_response(200)
            if body.get('stream'):
                self.send_header('Content-Type', 'text/event-stream')
                response = {'choices': [{'index': 0, 'delta': {'content': 'ok'}, 'finish_reason': None}]}
                payload = ('data: ' + json.dumps(response) + '\n\ndata: [DONE]\n\n').encode()
            else:
                self.send_header('Content-Type', 'application/json')
                payload = json.dumps({'choices': [{'message': {'role': 'assistant', 'content': 'ok'}}]}).encode()
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    monkeypatch.setattr('time.sleep', lambda _: None)
    monkeypatch.setenv('NO_PROXY', '127.0.0.1')
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01})
    worker.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', state
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


def make_model(provider, url, max_retries):
    cfg = {
        'model_type': provider,
        'model': 'test-model',
        'api_key': 'unused',
        'generate_cfg': {
            'max_retries': max_retries
        }
    }
    if provider == 'azure':
        cfg.update(azure_endpoint=url, api_version='2024-06-01')
    else:
        cfg['model_server'] = url + '/v1'
    return get_chat_model(cfg)


@pytest.mark.parametrize('provider', ['oai', 'azure'])
@pytest.mark.parametrize('max_retries', [0, 2])
@pytest.mark.parametrize('stream,delta_stream', [(False, False), (True, False), (True, True)])
def test_chat_retry_budget_bounds_http_attempts(endpoint, provider, max_retries, stream, delta_stream):
    """SDK retries must not multiply the framework's configured attempts."""
    url, state = endpoint
    model = make_model(provider, url, max_retries)
    with pytest.raises(ModelServiceError):
        response = model.chat([{'role': 'user', 'content': 'hello'}], stream=stream, delta_stream=delta_stream)
        if stream:
            list(response)
    assert len(state['requests']) == (1 if delta_stream else max_retries + 1)
    assert all('max_retries' not in body for body in state['requests'])


@pytest.mark.parametrize('provider', ['oai', 'azure'])
@pytest.mark.parametrize('stream', [False, True])
def test_chat_recovers_within_framework_retry_budget(endpoint, provider, stream):
    """Disabling SDK retries still allows the framework to recover."""
    url, state = endpoint
    state['failures'] = 2
    model = make_model(provider, url, max_retries=2)
    response = model.chat([{'role': 'user', 'content': 'hello'}], stream=stream)
    if stream:
        response = list(response)[-1]
    assert response[-1]['content'] == 'ok'
    assert len(state['requests']) == 3


def test_completion_does_not_add_sdk_retries(endpoint):
    """The completion adapter shares the same client retry policy."""
    url, state = endpoint
    model = make_model('oai', url, max_retries=0)
    with pytest.raises(openai.OpenAIError):
        model._complete_create(model=model.model, prompt='hello')
    assert len(state['requests']) == 1
