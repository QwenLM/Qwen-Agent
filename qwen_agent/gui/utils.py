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
