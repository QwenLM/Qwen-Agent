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

import copy
import json
import socket

import openai
import pytest

from qwen_agent.llm import ModelServiceError, get_chat_model
from qwen_agent.llm.schema import Message

httpx = pytest.importorskip('httpx')
pytest.importorskip('diskcache')
pytestmark = pytest.mark.skipif(not hasattr(openai, 'OpenAI'), reason='Requires the OpenAI 1.x or later HTTP client')


@pytest.fixture
def cached_model(monkeypatch, tmp_path):
    requests = []
    models = []

    def reject_network(*args, **kwargs):
        raise AssertionError('Response cache tests must not access the network.')

    monkeypatch.setattr(socket.socket, 'connect', reject_network)
    monkeypatch.setattr(socket.socket, 'connect_ex', reject_network)

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        if body['messages'][-1]['content'] == 'Raise a provider error.':
            return httpx.Response(400,
                                  json={'error': {
                                      'message': 'Offline test error',
                                      'type': 'invalid_request_error'
                                  }})
        content = 'Offline answer'
        if body['stream']:
            chunks = [{
                'id': 'offline',
                'created': 0,
                'object': 'chat.completion.chunk',
                'model': 'offline',
                'choices': [{
                    'index': 0,
                    'delta': {
                        'content': part
                    },
                    'finish_reason': None
                }],
            } for part in ['Offline ', 'answer']]
            data = ''.join(f'data: {json.dumps(chunk)}\n\n' for chunk in chunks) + 'data: [DONE]\n\n'
            return httpx.Response(200, text=data, headers={'content-type': 'text/event-stream'})
        return httpx.Response(200,
                              json={
                                  'id':
                                      'offline',
                                  'created':
                                      0,
                                  'object':
                                      'chat.completion',
                                  'model':
                                      'offline',
                                  'choices': [{
                                      'index': 0,
                                      'finish_reason': 'stop',
                                      'message': {
                                          'role': 'assistant',
                                          'content': content
                                      },
                                  }],
                              })

    client = openai.OpenAI(api_key='test-only',
                           base_url='https://offline.invalid/v1',
                           http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(openai, 'OpenAI', lambda **kwargs: client)

    def make_model(enabled=True, nested_config=False):
        cfg = {'model': 'offline', 'model_type': 'oai', 'api_key': 'test-only', 'generate_cfg': {'use_raw_api': False}}
        if enabled:
            target = cfg['generate_cfg'] if nested_config else cfg
            target['cache_dir'] = str(tmp_path / 'response-cache')
        model = get_chat_model(cfg)
        models.append(model)
        return model, requests

    yield make_model
    for model in models:
        if model.cache is not None:
            model.cache.close()
    client.close()


@pytest.mark.parametrize('message_objects', [False, True], ids=['dict', 'message'])
@pytest.mark.parametrize('nested_config', [False, True], ids=['top_level_cache', 'generate_cfg_cache'])
def test_nonstream_populates_empty_response_cache(cached_model, message_objects, nested_config):
    model, requests = cached_model(nested_config=nested_config)
    messages = [Message('user', 'Hello')] if message_objects else [{'role': 'user', 'content': 'Hello'}]
    original = copy.deepcopy(messages)
    assert len(model.cache) == 0

    first = model.chat(messages, stream=False)
    second = model.chat(messages, stream=False)

    assert first == second
    assert first[0]['content'] == 'Offline answer'
    assert isinstance(second[0], Message if message_objects else dict)
    assert len(requests) == 1
    assert len(model.cache) == 1
    assert messages == original


def test_nonstream_without_cache_calls_provider_each_time(cached_model):
    model, requests = cached_model(enabled=False)
    messages = [{'role': 'user', 'content': 'Hello'}]

    assert model.chat(messages, stream=False) == model.chat(messages, stream=False)
    assert model.cache is None
    assert len(requests) == 2


def test_nonstream_preserves_existing_cache_entries(cached_model):
    model, requests = cached_model()
    model.cache.set('existing-entry', 'unchanged')
    messages = [{'role': 'user', 'content': 'Hello'}]

    assert model.chat(messages, stream=False) == model.chat(messages, stream=False)
    assert len(requests) == 1
    assert len(model.cache) == 2
    assert model.cache.get('existing-entry') == 'unchanged'


def test_nonstream_repopulates_cleared_cache(cached_model):
    model, requests = cached_model()
    model.cache.set('existing-entry', 'unchanged')
    messages = [{'role': 'user', 'content': 'Hello'}]
    first = model.chat(messages, stream=False)
    model.cache.clear()

    assert model.chat(messages, stream=False) == first
    assert model.chat(messages, stream=False) == first
    assert len(requests) == 2
    assert len(model.cache) == 1


@pytest.mark.parametrize('change', ['messages', 'extra_generate_cfg'])
def test_nonstream_caches_distinct_requests_separately(cached_model, change):
    model, requests = cached_model()
    first = {'messages': [{'role': 'user', 'content': 'Hello'}], 'stream': False}
    second = copy.deepcopy(first)
    if change == 'messages':
        second['messages'][0]['content'] = 'Another question'
    else:
        second['extra_generate_cfg'] = {'temperature': 0.5}

    for kwargs in [first, second, first, second]:
        assert model.chat(**kwargs)[0]['content'] == 'Offline answer'

    assert len(requests) == 2
    assert len(model.cache) == 2


@pytest.mark.parametrize('first_stream', [False, True], ids=['nonstream_to_stream', 'stream_to_nonstream'])
def test_response_cache_shared_between_stream_modes(cached_model, first_stream):
    model, requests = cached_model()
    messages = [{'role': 'user', 'content': 'Hello'}]
    first = model.chat(messages, stream=first_stream)
    first = list(first)[-1] if first_stream else first
    second = model.chat(messages, stream=not first_stream)
    second = second if first_stream else list(second)[-1]

    assert first == second == [{'role': 'assistant', 'content': 'Offline answer'}]
    assert len(requests) == 1
    assert len(model.cache) == 1


def test_nonstream_response_cache_survives_model_recreation(cached_model):
    model, requests = cached_model()
    messages = [{'role': 'user', 'content': 'Hello'}]
    first = model.chat(messages, stream=False)
    model.cache.close()
    replacement, _ = cached_model()

    assert replacement.chat(messages, stream=False) == first
    assert len(requests) == 1


def test_failed_request_does_not_populate_cache(cached_model):
    model, requests = cached_model()
    for _ in range(2):
        with pytest.raises(ModelServiceError, match='Offline test error'):
            model.chat([{'role': 'user', 'content': 'Raise a provider error.'}], stream=False)
    assert len(requests) == 2
    assert len(model.cache) == 0

    messages = [{'role': 'user', 'content': 'Hello'}]
    assert model.chat(messages, stream=False) == model.chat(messages, stream=False)
    assert len(requests) == 3
    assert len(model.cache) == 1
