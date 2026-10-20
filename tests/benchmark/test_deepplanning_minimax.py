"""Exercise DeepPlanning's MiniMax configurations without network access."""

import importlib.util
import json
from functools import partial
from pathlib import Path

import httpx
import openai
import pytest

DEEPPLANNING = Path(__file__).resolve().parents[2] / 'benchmark' / 'deepplanning'
MODELS = ['MiniMax-M3.1-Flash', 'MiniMax-M3']


@pytest.fixture(params=['shoppingplanning', 'travelplanning'])
def caller(request):
    path = DEEPPLANNING / request.param / 'agent' / 'call_llm.py'
    spec = importlib.util.spec_from_file_location(f'{request.param}_call_llm', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def requests(monkeypatch):
    captured = []

    def respond(request):
        captured.append((str(request.url), json.loads(request.content)))
        return httpx.Response(200,
                              json={
                                  'id': 'test-completion',
                                  'object': 'chat.completion',
                                  'created': 0,
                                  'model': captured[-1][1]['model'],
                                  'choices': [{
                                      'index': 0,
                                      'message': {
                                          'role': 'assistant',
                                          'content': 'Plan complete.'
                                      },
                                      'finish_reason': 'stop'
                                  }]
                              })

    monkeypatch.setenv('MINIMAX_API_KEY', 'offline-test-key')
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(openai, 'OpenAI', partial(openai.OpenAI, http_client=client, max_retries=0))
        yield captured


def save_domain_config(caller, monkeypatch, tmp_path, name, model, base_url, extra_body=None):
    domain = tmp_path / 'domain'
    domain.mkdir()
    config = {
        'model_name': model,
        'model_type': 'openai',
        'base_url': base_url,
        'api_key_env': 'MINIMAX_API_KEY',
        'max_retries': 1
    }
    if extra_body:
        config['extra_body'] = extra_body
    (domain / 'models_config.json').write_text(json.dumps({'models': {name: config}}))
    monkeypatch.setattr(caller, '__file__', str(domain / 'agent' / 'call_llm.py'))


def test_catalog_order():
    models = json.loads((DEEPPLANNING / 'models_config.json').read_text())['models']
    assert [name for name in models if name.startswith('MiniMax-')] == MODELS


@pytest.mark.parametrize('model', MODELS)
def test_catalog_request(caller, requests, model):
    messages = [{'role': 'user', 'content': 'Plan a trip.'}]
    response = caller.call_llm(model, messages)
    assert response.choices[0].message.content == 'Plan complete.'
    assert requests == [('https://api.minimax.io/v1/chat/completions', {'model': model, 'messages': messages})]


@pytest.mark.parametrize('model', ['MiniMax-M2.7', 'my-custom-model'])
@pytest.mark.parametrize('base_url', ['https://api.minimax.io/v1', 'https://api.minimaxi.com/v1'])
def test_saved_domain_config(caller, requests, monkeypatch, tmp_path, model, base_url):
    save_domain_config(caller, monkeypatch, tmp_path, 'saved-choice', model, base_url)
    messages = [{'role': 'user', 'content': 'Keep this saved model.'}]
    caller.call_llm('saved-choice', messages)
    assert requests == [(f'{base_url}/chat/completions', {'model': model, 'messages': messages})]


@pytest.mark.parametrize('effort', ['low', 'medium', 'high', 'xhigh', 'max'])
def test_flash_effort_and_history(caller, requests, monkeypatch, tmp_path, effort):
    extra_body = {'reasoning_effort': effort, 'thinking': {'type': 'adaptive'}}
    save_domain_config(caller, monkeypatch, tmp_path, 'saved-flash', MODELS[0], 'https://api.minimax.io/v1',
                       extra_body)
    tools = [{'type': 'function', 'function': {'name': 'lookup', 'parameters': {'type': 'object'}}}]
    messages = [{
        'role': 'user',
        'content': [{'type': 'text', 'text': 'Plan from this image.'},
                    {'type': 'image_url', 'image_url': {'url': 'https://example.invalid/map.png'}},
                    {'type': 'video_url', 'video_url': {'url': 'https://example.invalid/route.mp4'}}]
    }, {
        'role': 'assistant',
        'content': None,
        'reasoning_content': 'Check the route.',
        'tool_calls': [{'id': 'call_1', 'type': 'function', 'function': {'name': 'lookup', 'arguments': '{}'}}]
    }, {
        'role': 'tool',
        'tool_call_id': 'call_1',
        'content': 'Route available.'
    }]
    caller.call_llm('saved-flash', messages, tools)
    assert requests == [('https://api.minimax.io/v1/chat/completions', {
        'model': MODELS[0], 'messages': messages, 'tools': tools, **extra_body
    })]


@pytest.mark.parametrize('thinking', ['adaptive', 'disabled'])
def test_m3_thinking(caller, requests, monkeypatch, tmp_path, thinking):
    extra_body = {'thinking': {'type': thinking}}
    save_domain_config(caller, monkeypatch, tmp_path, 'saved-m3', MODELS[1], 'https://api.minimax.io/v1', extra_body)
    messages = [{'role': 'user', 'content': 'Plan a trip.'}]
    caller.call_llm('saved-m3', messages)
    assert requests == [('https://api.minimax.io/v1/chat/completions', {
        'model': MODELS[1], 'messages': messages, **extra_body
    })]
