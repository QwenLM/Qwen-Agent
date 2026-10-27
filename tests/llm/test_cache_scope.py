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

from qwen_agent.llm.oai import TextChatAtOAI
from qwen_agent.llm.schema import Message

httpx = pytest.importorskip('httpx')
pytest.importorskip('diskcache')
pytestmark = pytest.mark.skipif(not hasattr(openai, 'OpenAI'), reason='Requires the OpenAI 1.x or later client')


class OtherBackend(TextChatAtOAI):
    pass


@pytest.fixture
def models(monkeypatch, tmp_path):
    calls = []
    clients = []
    instances = []
    original_client = openai.OpenAI

    def reject_network(*args, **kwargs):
        raise AssertionError('Cache tests must not access the network.')

    monkeypatch.setattr(socket.socket, 'connect', reject_network)
    monkeypatch.setattr(socket.socket, 'connect_ex', reject_network)

    def respond(request):
        body = json.loads(request.content)
        calls.append((str(request.url), body))
        answer = f"{request.url.host}/{body['model']}/{body.get('temperature')}/{body.get('top_p')}"
        if body['stream']:
            chunks = [{
                'id': 'offline',
                'created': 0,
                'object': 'chat.completion.chunk',
                'model': body['model'],
                'choices': [{
                    'index': 0,
                    'delta': {
                        'content': part
                    },
                    'finish_reason': None
                }],
            } for part in [answer[:3], answer[3:]]]
            data = ''.join(f'data: {json.dumps(chunk)}\n\n' for chunk in chunks) + 'data: [DONE]\n\n'
            return httpx.Response(200, text=data, headers={'content-type': 'text/event-stream'})
        return httpx.Response(
            200,
            json={
                'id': 'offline',
                'created': 0,
                'object': 'chat.completion',
                'model': body['model'],
                'choices': [{
                    'index': 0,
                    'finish_reason': 'stop',
                    'message': {
                        'role': 'assistant',
                        'content': answer
                    }
                }],
            })

    def client(**kwargs):
        instance = original_client(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))
        clients.append(instance)
        return instance

    monkeypatch.setattr(openai, 'OpenAI', client)

    def make(changes=None, backend=TextChatAtOAI):
        cfg = {
            'model': 'first',
            'model_type': 'oai',
            'api_key': 'test-only',
            'cache_dir': str(tmp_path / 'cache'),
            'api_base': 'https://first.invalid/v1',
            'generate_cfg': {
                'temperature': 0.25,
                'use_raw_api': False
            },
        }
        cfg.update(copy.deepcopy(changes or {}))
        instance = backend(cfg)
        instances.append(instance)
        return instance

    yield make, calls
    for instance in instances:
        if instance.cache is not None:
            instance.cache.close()
    for client in clients:
        client.close()


def chat(model, stream=True, extra=None, message_objects=False):
    messages = [Message('user', 'Hello')] if message_objects else [{'role': 'user', 'content': 'Hello'}]
    original = copy.deepcopy(messages)
    response = model.chat(messages, stream=stream, extra_generate_cfg=extra)
    response = list(response)[-1] if stream else response
    assert messages == original
    assert isinstance(response[0], Message if message_objects else dict)
    return response[0]['content']


@pytest.mark.parametrize('stream', [True, False], ids=['stream', 'nonstream'])
@pytest.mark.parametrize('change', ['model', 'temperature', 'top_p', 'api_base', 'base_url', 'model_server', 'backend'])
def test_shared_cache_separates_model_configuration(models, change, stream):
    make, calls = models
    first = make()
    if change == 'model':
        second = make({'model': 'second'})
    elif change == 'temperature':
        second = make({'generate_cfg': {'temperature': 0.75, 'use_raw_api': False}})
    elif change == 'top_p':
        second = make({'generate_cfg': {'temperature': 0.25, 'top_p': 0.5, 'use_raw_api': False}})
    elif change == 'backend':
        second = make(backend=OtherBackend)
    else:
        second = make({'api_base': None, change: 'https://second.invalid/v1'})

    first_answer = chat(first)
    second_answer = chat(second, stream=stream)
    assert len(calls) == 2
    if change != 'backend':
        assert first_answer != second_answer
    assert chat(first, stream=stream) == first_answer
    assert chat(second, stream=stream) == second_answer
    assert len(calls) == 2


@pytest.mark.parametrize('stream', [True, False])
@pytest.mark.parametrize('message_objects', [True, False])
def test_same_configuration_reuses_cache_after_recreation(models, stream, message_objects):
    make, calls = models
    answer = chat(make(), message_objects=message_objects)
    assert chat(make(), stream=stream, message_objects=message_objects) == answer
    assert len(calls) == 1


def test_cache_uses_merged_generation_settings(models):
    make, calls = models
    first = make()
    answer = chat(first)
    second = make({'generate_cfg': {'temperature': 0.75, 'use_raw_api': False}})
    assert chat(second, extra={'temperature': 0.25}) == answer
    assert len(calls) == 1
    distinct = chat(first, extra={'temperature': 0.75})
    assert distinct != answer
    assert len(calls) == 2
    assert chat(second) == distinct
    assert len(calls) == 2


def test_model_generation_setting_changes_invalidate_cache(models):
    make, calls = models
    model = make()
    answer = chat(model)
    model.generate_cfg['temperature'] = 0.75
    assert chat(model) != answer
    assert len(calls) == 2


def test_legacy_unscoped_entries_are_not_reused(models):
    make, calls = models
    model = make()
    from qwen_agent.utils.utils import json_dumps_compact
    key = json_dumps_compact(dict(messages=[Message('user', 'Hello')], functions=None, extra_generate_cfg=None),
                             sort_keys=True)
    model.cache.set(key, json.dumps([{'role': 'assistant', 'content': 'wrong legacy model answer'}]))
    assert chat(model) != 'wrong legacy model answer'
    assert len(calls) == 1


@pytest.mark.parametrize('stream', [True, False])
def test_disabled_cache_does_not_reuse_responses(models, stream):
    make, calls = models
    model = make({'cache_dir': None})
    assert chat(model, stream=stream) == chat(model, stream=stream)
    assert model.cache is None
    assert len(calls) == 2


def test_explicit_seed_remains_part_of_request_identity(models):
    make, calls = models
    model = make()
    chat(model, extra={'seed': 1})
    chat(model, extra={'seed': 2})
    assert len(calls) == 2
    chat(model, extra={'seed': 1})
    assert len(calls) == 2
    assert [call[1]['seed'] for call in calls] == [1, 2]


def test_function_definitions_remain_part_of_request_identity(models):
    make, calls = models
    model = make()
    messages = [{'role': 'user', 'content': 'Hello'}]
    first = [{'name': 'read_first', 'description': 'First tool', 'parameters': {'type': 'object', 'properties': {}}}]
    second = [{'name': 'read_second', 'description': 'Second tool', 'parameters': {'type': 'object', 'properties': {}}}]
    for functions in [first, second, first, second]:
        assert list(model.chat(messages, functions=functions))[-1][0]['role'] == 'assistant'
    assert len(calls) == 2


def test_raw_api_mode_does_not_reuse_processed_response(models):
    make, calls = models
    answer = chat(make())
    raw = make({'generate_cfg': {'temperature': 0.25, 'use_raw_api': True}})
    assert chat(raw, message_objects=True) == answer
    assert len(calls) == 2


def test_cache_identity_does_not_persist_api_key(models):
    make, calls = models
    model = make()
    chat(model)
    assert len(calls) == 1
    assert all('test-only' not in key for key in model.cache.iterkeys())
