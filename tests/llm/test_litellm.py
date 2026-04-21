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

import os
from types import SimpleNamespace

import pytest

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.base import LLM_REGISTRY
from qwen_agent.llm.litellm import TextChatAtLiteLLM
from qwen_agent.llm.schema import Message


def _non_stream_response(content: str = 'Hello from LiteLLM') -> SimpleNamespace:
    """Build a fake LiteLLM ModelResponse-shaped object (OpenAI-compatible)."""
    message = SimpleNamespace(content=content, reasoning_content=None)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def _stream_chunks(content: str = 'Hello from LiteLLM'):
    """Yield OpenAI-compatible streaming chunks from LiteLLM."""
    delta = SimpleNamespace(content=content, reasoning_content=None, tool_calls=None)
    choice = SimpleNamespace(delta=delta)
    yield SimpleNamespace(choices=[choice])


def test_litellm_registered():
    assert 'litellm' in LLM_REGISTRY
    assert LLM_REGISTRY['litellm'] is TextChatAtLiteLLM


def test_litellm_get_chat_model():
    cfg = {'model': 'openai/gpt-4o-mini', 'model_type': 'litellm', 'api_key': 'sk-fake'}
    llm = get_chat_model(cfg)
    assert isinstance(llm, TextChatAtLiteLLM)
    assert llm.model == 'openai/gpt-4o-mini'


def test_litellm_call_kwargs_forwards_api_key_and_base():
    cfg = {
        'model': 'openrouter/meta-llama/llama-3-70b-instruct',
        'model_type': 'litellm',
        'api_key': 'sk-fake',
        'api_base': 'https://my-proxy.example.com/v1',
    }
    llm = get_chat_model(cfg)
    kwargs = llm._call_kwargs(messages=[{'role': 'user', 'content': 'hi'}], generate_cfg={}, stream=False)
    assert kwargs['model'] == 'openrouter/meta-llama/llama-3-70b-instruct'
    assert kwargs['api_key'] == 'sk-fake'
    assert kwargs['api_base'] == 'https://my-proxy.example.com/v1'
    assert kwargs['stream'] is False


def test_litellm_no_stream(mocker):
    mocker.patch('litellm.completion', return_value=_non_stream_response('pong'))
    cfg = {'model': 'openai/gpt-4o-mini', 'model_type': 'litellm', 'api_key': 'sk-fake'}
    llm = get_chat_model(cfg)
    response = llm.chat(messages=[Message('user', 'ping')], stream=False)
    assert response[-1]['content'] == 'pong'


def test_litellm_stream(mocker):
    mocker.patch('litellm.completion', return_value=_stream_chunks('streamed reply'))
    cfg = {'model': 'openai/gpt-4o-mini', 'model_type': 'litellm', 'api_key': 'sk-fake'}
    llm = get_chat_model(cfg)
    final = list(llm.chat(messages=[Message('user', 'ping')], stream=True))[-1]
    assert 'streamed reply' in final[-1]['content']


@pytest.mark.skipif(not os.getenv('OPENAI_API_KEY'), reason='OPENAI_API_KEY not set')
def test_litellm_integration_openai():
    """Live integration smoke test — only runs when OPENAI_API_KEY is exported."""
    cfg = {
        'model': 'openai/gpt-4o-mini',
        'model_type': 'litellm',
        'api_key': os.getenv('OPENAI_API_KEY'),
    }
    llm = get_chat_model(cfg)
    response = llm.chat(messages=[Message('user', 'Say "pong" and nothing else.')], stream=False)
    assert isinstance(response[-1]['content'], str)
    assert response[-1]['content'].strip() != ''
