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

"""Structured (native) tool calls must survive both stream modes.

The requests are served by a canned transport, so this module needs neither
network access nor an API key.
"""

from types import SimpleNamespace

import pytest

from qwen_agent.llm.oai import TextChatAtOAI
from qwen_agent.llm.schema import Message

FUNCTIONS = [{
    'name': 'get_weather',
    'description': 'Get the current weather in a given location',
    'parameters': {
        'type': 'object',
        'properties': {
            'city': {
                'type': 'string'
            }
        },
        'required': ['city'],
    },
}]

MESSAGES = [Message('user', 'What is the weather in Paris?')]

TOOL_NAME = 'get_weather'
TOOL_ARGS = '{"city": "Paris"}'


def _tool_call():
    return SimpleNamespace(id='call_abc', index=0, type='function', function=SimpleNamespace(
        name=TOOL_NAME, arguments=TOOL_ARGS))


def _stream_chunk():
    delta = SimpleNamespace(content=None, tool_calls=[_tool_call()])
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _chat_completion():
    message = SimpleNamespace(content=None, reasoning_content=None, tool_calls=[_tool_call()])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeTransportOAI(TextChatAtOAI):
    """OpenAI-compatible client whose transport returns canned data."""

    def __init__(self):
        super().__init__({'model': 'fake-model', 'api_key': 'EMPTY', 'generate_cfg': {'max_retries': 0}})
        # __init__ binds the real client on the instance, so replace it after the fact.
        self._chat_complete_create = self._fake_chat_complete_create

    @staticmethod
    def _fake_chat_complete_create(*args, **kwargs):
        if kwargs.get('stream'):
            return iter([_stream_chunk()])
        return _chat_completion()


@pytest.mark.parametrize('stream', [True, False])
def test_native_tool_call_is_kept(stream):
    llm = FakeTransportOAI()
    response = llm.chat(messages=MESSAGES, functions=FUNCTIONS, stream=stream)
    if stream:
        response = list(response)[-1]

    assert len(response) == 1
    assert response[-1].function_call.name == TOOL_NAME
    assert response[-1].function_call.arguments == TOOL_ARGS
