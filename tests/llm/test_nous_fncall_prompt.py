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

import pytest

from qwen_agent.llm.fncall_prompts.nous_fncall_prompt import NousFnCallPrompt, extract_fn
from qwen_agent.llm.schema import ASSISTANT, ContentItem, Message

# Assembled from fragments so this file never contains a literal tool-call tag.
TOOL_CALL_OPEN = '<' + 'tool_' + 'call' + '>'
TOOL_CALL_CLOSE = '<' + '/' + 'tool_' + 'call' + '>'

# The same call written twice: once with the spaces a pretty-printer emits, once
# compact. Both are valid JSON, so both must decode to the same tool call.
COMPACT = '{"name":"get_weather","arguments":{"city":"Beijing"}}'
SPACED = '{"name": "get_weather", "arguments": {"city": "Beijing"}}'
# A stream cut mid-arguments, still carrying a complete name.
TRUNCATED_COMPACT = '{"name":"get_weather","arguments":{"city":"Bei'
TRUNCATED_SPACED = '{"name": "get_weather", "arguments": {"city": "Bei'


@pytest.mark.parametrize(('text', 'arguments'), [
    (SPACED, '{"city": "Beijing"}'),
    (COMPACT, '{"city":"Beijing"}'),
])
def test_extract_fn_parses_compact_and_spaced_json_identically(text, arguments):
    # Whitespace inside the payload is not normalised, but both spellings must
    # recover the same tool name and an equivalent arguments object.
    name, recovered = extract_fn(text)

    assert name == 'get_weather'
    assert recovered == arguments
    assert json.loads(recovered) == {'city': 'Beijing'}


@pytest.mark.parametrize(('text', 'arguments'), [
    (TRUNCATED_SPACED, '{"city": "Bei'),
    (TRUNCATED_COMPACT, '{"city":"Bei'),
])
def test_extract_fn_keeps_name_from_truncated_stream_chunk(text, arguments):
    # The name is already complete when a stream is cut mid-arguments, so a
    # partial tool call must still carry it instead of collapsing to an empty
    # name and being dropped by the `if fn_name:` guard.
    name, recovered = extract_fn(text)

    assert name == 'get_weather'
    assert recovered == arguments


@pytest.mark.parametrize('payload', [TRUNCATED_SPACED, TRUNCATED_COMPACT])
def test_postprocess_keeps_tool_call_from_truncated_json(payload):
    # json5 rejects these payloads, which routes the fallback parser. That
    # fallback appends a function_call without an `if fn_name:` guard, so an
    # empty name would reach the agent as a call it cannot dispatch.
    text = TOOL_CALL_OPEN + chr(10) + payload + chr(10)
    messages = [Message(role=ASSISTANT, content=[ContentItem(text=text)])]

    parsed = NousFnCallPrompt().postprocess_fncall_messages(messages)

    assert parsed[-1].function_call.name == 'get_weather'
