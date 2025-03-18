import json
from typing import List

from qwen_agent.llm.schema import ASSISTANT, FUNCTION

TOOL_CALL_S = '[TOOL_CALL]'
TOOL_CALL_E = ''
TOOL_RESULT_S = '[TOOL_RESPONSE]'
TOOL_RESULT_E = ''
THOUGHT_S = '[THINK]'

CODE_INTERPRETER = 'code_interpreter'


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
                content.append(msg['content'])
            if msg.get('function_call'):
                if msg['function_call']['name'] == CODE_INTERPRETER:
                    try:
                        _code = json.loads(msg['function_call']['arguments'])['code']
                        content.append(f'{TOOL_CALL_S} {msg["function_call"]["name"]}\n{_code}')
                    except Exception:
                        content.append(
                            f'{TOOL_CALL_S} {msg["function_call"]["name"]}\n{msg["function_call"]["arguments"]}')

                else:
                    content.append(f'{TOOL_CALL_S} {msg["function_call"]["name"]}\n{msg["function_call"]["arguments"]}')
        elif msg['role'] == FUNCTION:
            content.append(f'{TOOL_RESULT_S} {msg["name"]}\n{msg["content"]}')
        else:
            raise TypeError
    if content:
        full_text = '\n'.join(content)
        print(full_text[len(text):], end='', flush=True)

    return full_text
