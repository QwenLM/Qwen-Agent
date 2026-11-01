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

import httpx
import openai
import pytest

from qwen_agent.llm.azure import TextChatAtAzure
from qwen_agent.llm.schema import Message


@pytest.mark.parametrize('stream', [False, True])
@pytest.mark.parametrize(
    'config_key,azure_key,openai_key,expected_key', [
        (None, 'azure-key', None, 'azure-key'),
        ('config-key', 'azure-key', 'openai-key', 'config-key'),
        (None, 'azure-key', 'openai-key', 'azure-key'),
        (None, None, 'openai-key', 'openai-key'),
        (None, None, None, 'EMPTY'),
    ],
    ids=['azure-only', 'explicit-config', 'azure-before-openai', 'openai-fallback', 'empty-fallback'])
def test_azure_api_key_resolution(monkeypatch, stream, config_key, azure_key, openai_key, expected_key):
    for variable, value in [('AZURE_OPENAI_API_KEY', azure_key), ('OPENAI_API_KEY', openai_key),
                            ('AZURE_OPENAI_AD_TOKEN', None)]:
        if value is None:
            monkeypatch.delenv(variable, raising=False)
        else:
            monkeypatch.setenv(variable, value)

    requests = []
    clients = []
    azure_client = openai.AzureOpenAI

    def handle_request(request):
        requests.append(request)
        if json.loads(request.content)['stream']:
            chunk = {
                'id': 'offline',
                'object': 'chat.completion.chunk',
                'created': 0,
                'model': 'test-deployment',
                'choices': [{
                    'index': 0,
                    'delta': {
                        'role': 'assistant',
                        'content': 'hello'
                    },
                    'finish_reason': None
                }],
            }
            body = 'data: ' + json.dumps(chunk) + '\n\ndata: [DONE]\n\n'
            return httpx.Response(200, headers={'Content-Type': 'text/event-stream'}, content=body)
        return httpx.Response(200,
                              json={
                                  'id':
                                      'offline',
                                  'object':
                                      'chat.completion',
                                  'created':
                                      0,
                                  'model':
                                      'test-deployment',
                                  'choices': [{
                                      'index': 0,
                                      'message': {
                                          'role': 'assistant',
                                          'content': 'hello'
                                      },
                                      'finish_reason': 'stop'
                                  }],
                              })

    def create_client(**kwargs):
        client = azure_client(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle_request)))
        clients.append(client)
        return client

    monkeypatch.setattr('qwen_agent.llm.azure.openai.AzureOpenAI', create_client)
    cfg = {'model': 'test-deployment', 'azure_endpoint': 'https://example.invalid'}
    if config_key is not None:
        cfg['api_key'] = config_key
    model = TextChatAtAzure(cfg)

    try:
        response = model.chat(messages=[Message(role='user', content='hello')], stream=stream)
        if stream:
            response = list(response)[-1]

        assert response[-1].content == 'hello'
        assert len(requests) == 1
        assert requests[0].headers['api-key'] == expected_key
    finally:
        for client in clients:
            client.close()
