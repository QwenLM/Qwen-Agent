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
from typing import Dict, List

from qwen_agent.llm.schema import ASSISTANT, CONTENT, FUNCTION, NAME, REASONING_CONTENT, ROLE, SYSTEM, USER

THINK = '''
<details open>
  <summary>Thinking ...</summary>

<div style="color: gray;">{thought}</div>
</details>
'''

TOOL_CALL = '''
<details>
  <summary>Start calling tool "{tool_name}" ...</summary>

{tool_input}
</details>
'''

TOOL_OUTPUT = '''
<details>
  <summary>Finished tool calling.</summary>

{tool_output}
</details>

'''


def get_avatar_image(name: str = 'user') -> str:
    if name == 'user':
        return os.path.join(os.path.dirname(__file__), 'assets/user.jpeg')

    return os.path.join(os.path.dirname(__file__), 'assets/logo.jpeg')


def convert_history_to_chatbot(messages):
    if not messages:
        return None
    chatbot_history = [[None, None]]
    for message in messages:
        if message.keys() != {'role', 'content'}:
            raise ValueError('Each message must be a dict containing only "role" and "content".')
        if message['role'] == USER:
            chatbot_history[-1][0] = message['content']
        elif message['role'] == ASSISTANT:
            chatbot_history[-1][1] = message['content']
            chatbot_history.append([None, None])
        else:
            raise ValueError(f'Message role must be {USER} or {ASSISTANT}.')
    return chatbot_history


def convert_fncall_to_text(messages: List[Dict]) -> List[Dict]:
    new_messages = []

    for msg in messages:
        role, content, reasoning_content, name = msg[ROLE], msg[CONTENT], msg.get(REASONING_CONTENT,
                                                                                  ''), msg.get(NAME, None)
        content = (content or '').lstrip('\n').rstrip().replace('```', '')

        # if role is system or user, just append the message
        if role in (SYSTEM, USER):
            new_messages.append({ROLE: role, CONTENT: content, NAME: name})

        # if role is assistant, append the message and add function call details
        elif role == ASSISTANT:
            if reasoning_content:
                thought = reasoning_content
                content = THINK.format(thought=thought) + content

            if '<think>' in content:
                ti = content.find('<think>')
                te = content.find('</think>')
                if te == -1:
                    te = len(content)
                thought = content[ti + len('<think>'):te]
                if thought.strip():
                    _content = content[:ti] + THINK.format(thought=thought)
                else:
                    _content = content[:ti]
                if te < len(content):
                    _content += content[te:]
                content = _content.strip('\n')

            fn_call = msg.get(f'{FUNCTION}_call', {})
            if fn_call:
                f_name = fn_call['name']
                f_args = fn_call['arguments']
                content += TOOL_CALL.format(tool_name=f_name, tool_input=f_args)
            if len(new_messages) > 0 and new_messages[-1][ROLE] == ASSISTANT and new_messages[-1][NAME] == name:
                new_messages[-1][CONTENT] += content
            else:
                new_messages.append({ROLE: role, CONTENT: content, NAME: name})

        # if role is function, append the message and add function result and exit details
        elif role == FUNCTION:
            assert new_messages[-1][ROLE] == ASSISTANT
            new_messages[-1][CONTENT] += TOOL_OUTPUT.format(tool_output=content)

        # if role is not system, user, assistant or function, raise TypeError
        else:
            raise TypeError

    return new_messages
