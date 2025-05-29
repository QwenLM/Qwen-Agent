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

from typing import List

from qwen_agent.llm.schema import ASSISTANT, FUNCTION

TOOL_CALL_S = '[TOOL_CALL]'
TOOL_CALL_E = ''
TOOL_RESULT_S = '[TOOL_RESPONSE]'
TOOL_RESULT_E = ''
THOUGHT_S = '[THINK]'
ANSWER_S = '[ANSWER]'


def typewriter_print(messages: List[dict], text: str) -> str:
    full_text = ''
    content = []
    for msg in messages:
        if msg['role'] == ASSISTANT:
            if msg.get('reasoning_content'):
                assert isinstance(msg['reasoning_content'], str), 'Now only supports text messages'
                content.append(f'{THOUGHT_S}\n{msg["reasoning_content"]}')
            if msg.get('content'):
                assert isinstance(msg['content'], str), 'Now only supports text messages'
                content.append(f'{ANSWER_S}\n{msg["content"]}')
            if msg.get('function_call'):
                content.append(f'{TOOL_CALL_S} {msg["function_call"]["name"]}\n{msg["function_call"]["arguments"]}')
        elif msg['role'] == FUNCTION:
            content.append(f'{TOOL_RESULT_S} {msg["name"]}\n{msg["content"]}')
        else:
            raise TypeError
    if content:
        full_text = '\n'.join(content)
        print(full_text[len(text):], end='', flush=True)

    return full_text
