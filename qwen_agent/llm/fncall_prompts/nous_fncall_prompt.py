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
import os
from typing import List, Literal, Union

import json5

from qwen_agent.llm.fncall_prompts.base_fncall_prompt import BaseFnCallPrompt
from qwen_agent.llm.schema import ASSISTANT, FUNCTION, SYSTEM, USER, ContentItem, FunctionCall, Message
from qwen_agent.log import logger


class NousFnCallPrompt(BaseFnCallPrompt):

    def preprocess_fncall_messages(self,
                                   messages: List[Message],
                                   functions: List[dict],
                                   lang: Literal['en', 'zh'],
                                   parallel_function_calls: bool = True,
                                   function_choice: Union[Literal['auto'], str] = 'auto',
                                   **kwargs) -> List[Message]:
        del lang  # ignored
        del parallel_function_calls  # ignored
        if function_choice != 'auto':
            raise NotImplementedError

        ori_messages = messages

        # Change function_call responses to plaintext responses:
        messages = []
        for msg in copy.deepcopy(ori_messages):
            role, content, reasoning_content = msg.role, msg.content, msg.reasoning_content
            if role in (SYSTEM, USER):
                messages.append(msg)
            elif role == ASSISTANT:
                content = (content or [])
                fn_call = msg.function_call
                if fn_call:
                    if (not SPECIAL_CODE_MODE) or (CODE_TOOL_PATTERN not in fn_call.name):
                        arguments = fn_call.arguments
                        try:
                            arguments = json5.loads(arguments)
                        except Exception:
                            logger.warning('Invalid json tool-calling arguments')
                        fc = {'name': fn_call.name, 'arguments': arguments}
                        fc = json.dumps(fc, ensure_ascii=False)
                        fc = f'<tool_call>\n{fc}\n</tool_call>'
                    else:
                        para = json5.loads(fn_call.arguments)
                        code = para['code']
                        para['code'] = ''
                        fc = {'name': fn_call.name, 'arguments': para}
                        fc = json.dumps(fc, ensure_ascii=False)
                        fc = f'<tool_call>\n{fc}\n<code>\n{code}\n</code>\n</tool_call>'

                    content.append(ContentItem(text=fc))
                if messages and messages[-1].role == ASSISTANT:
                    if messages[-1].content and messages[-1].content[-1].text and (
                            not messages[-1].content[-1].text.endswith('\n')):
                        messages[-1].content.append(ContentItem(text='\n'))
                    messages[-1].content.extend(content)
                else:
                    # TODO: Assuming there will only be one continuous reasoning_content here
                    messages.append(Message(role=role, content=content, reasoning_content=reasoning_content))
            elif role == FUNCTION:
                assert isinstance(content, list)
                content = [ContentItem(text='<tool_response>\n')] + content + [ContentItem(text='\n</tool_response>')]
                if messages[-1].role == USER:
                    messages[-1].content.append(ContentItem(text='\n'))
                    messages[-1].content.extend(content)
                else:
                    messages.append(Message(role=USER, content=content))
            else:
                raise TypeError

        tool_descs = [{'type': 'function', 'function': f} for f in functions]
        tool_names = [function.get('name_for_model', function.get('name', '')) for function in functions]
        tool_descs = '\n'.join([json.dumps(f, ensure_ascii=False) for f in tool_descs])
        if SPECIAL_CODE_MODE and any([CODE_TOOL_PATTERN in x for x in tool_names]):
            tool_system = FN_CALL_TEMPLATE_WITH_CI.format(tool_descs=tool_descs)
        else:
            tool_system = FN_CALL_TEMPLATE.format(tool_descs=tool_descs)
        if messages and messages[0].role == SYSTEM:
            messages[0].content.append(ContentItem(text='\n\n' + tool_system))
        else:
            messages = [Message(role=SYSTEM, content=[ContentItem(text=tool_system)])] + messages
        return messages
    
    def postprocess_fncall_messages(
        self,
        messages: List[Message],
        parallel_function_calls: bool = True,
        function_choice: Union[Literal['auto'], str] = 'auto',
        thought_in_content: bool = False,
    ) -> List[Message]:
        if function_choice != 'auto':
            raise NotImplementedError
        # Convert plaintext responses to function_call responses:
        new_messages = []
        tool_id = 1
        for msg in messages:
            role, content, reasoning_content, extra = msg.role, msg.content, msg.reasoning_content, msg.extra
            extra = extra or {}
            assert isinstance(content, list)

            if role in (SYSTEM, USER):
                new_messages.append(
                    Message(role=role, content=content, reasoning_content=reasoning_content, extra=extra))
                continue

            # Reasoning content is placed in a separate message
            if reasoning_content:
                new_messages.append(Message(role=role, content='', reasoning_content=reasoning_content, extra=extra))

            new_content = []
            for item in content:
                item_type, item_text = item.get_type_and_value()

                if item_type != 'text':  # multimodal
                    new_content.append(item)
                    continue
                # Do not parse <tool_call> in thought!!!
                if '<think>' in item_text:
                    thought_in_content = True
                if thought_in_content:
                    if '</think>' not in item_text:
                        new_content.append(ContentItem(text=item_text))
                        continue
                    _item_text = item_text.split('</think>')
                    # assert len(_item_text) == 2
                    new_content.append(ContentItem(text='</think>'.join(_item_text[:-1]) + '</think>'))
                    item_text = _item_text[-1]

                i = item_text.find('<tool_call>')
                # If no function call:
                if i < 0:
                    show_text = item_text
                    if show_text:
                        new_content.append(ContentItem(text=show_text))
                    continue

                # split tool-call to separate assistant msg
                tool_call_list = item_text.split('<tool_call>')
                pre_thought = tool_call_list[0]
                if pre_thought.strip():
                    new_content.append(ContentItem(text=pre_thought))
                for txt in tool_call_list[1:]:
                    if not txt.strip():
                        continue

                    if '</tool_call>' not in txt:
                        # incomplete </tool_call>: This is to better represent incomplete tool calls in streaming output
                        fn_name, fn_args = extract_fn(txt)
                        if fn_name:  # need to call function
                            if new_content:
                                new_messages.append(Message(
                                    role=role,
                                    content=new_content,
                                    extra=extra,
                                ))  # split thought and function call
                                new_content = []
                            # TODO: process incomplete tool-call messages
                            _extra = copy.deepcopy(extra) if extra else {'function_id': ''}
                            _extra['function_id'] = str(tool_id)
                            tool_id += 1
                            new_messages.append(
                                Message(
                                    role=ASSISTANT,
                                    content=[],
                                    function_call=FunctionCall(
                                        name=fn_name,
                                        arguments=fn_args,
                                    ),
                                    extra=_extra,
                                ))
                        continue

                    one_tool_call_txt = txt.split('</tool_call>')

                    # The complete tool-call response
                    if new_content:
                        new_messages.append(Message(
                            role=role,
                            content=new_content,
                            extra=extra,
                        ))  # split thought and function call
                        new_content = []
                    fn = None
                    if SPECIAL_CODE_MODE and '<code>' in one_tool_call_txt[0] and '</code>' in one_tool_call_txt[0]:
                        _snips = one_tool_call_txt[0].split('<code>')
                        for i, _s in enumerate(_snips):
                            if i == 0:
                                fn = json5.loads(_s)
                            else:
                                # TODO: support more flexible params
                                code = _s.replace('</code>', '')
                                fn['arguments']['code'] = code
                    else:
                        try:
                            fn = json5.loads(one_tool_call_txt[0].strip())
                        except Exception:
                            logger.warning('Invalid json tool-calling arguments')
                            fn_name, fn_args = extract_fn(one_tool_call_txt[0].strip())
                            _extra = copy.deepcopy(extra) if extra else {'function_id': ''}
                            _extra['function_id'] = str(tool_id)
                            tool_id += 1
                            new_messages.append(
                                Message(
                                    role=ASSISTANT,
                                    content=[],
                                    function_call=FunctionCall(
                                        name=fn_name,
                                        arguments=fn_args,
                                    ),
                                    extra=_extra,
                                ))
                    if fn and 'name' in fn and 'arguments' in fn:
                        _extra = copy.deepcopy(extra) if extra else {}
                        _extra['function_id'] = str(tool_id)
                        tool_id += 1
                        new_messages.append(
                            Message(
                                role=ASSISTANT,
                                content=[],
                                function_call=FunctionCall(
                                    name=fn['name'],
                                    arguments=json.dumps(fn['arguments'], ensure_ascii=False),
                                ),
                                extra=_extra,
                            ))
                    # Expected not to output extra tails
                    # if one_tool_call_txt[1].strip():
                    #     new_content.append(ContentItem(text=one_tool_call_txt[1]))

            if new_content:
                new_messages.append(Message(role=role, content=new_content, extra=extra))
        return new_messages


FN_CALL_TEMPLATE = """# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tool_descs}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{{"name": <function-name>, "arguments": <args-json-object>}}
</tool_call>"""

SPECIAL_CODE_MODE = os.getenv('SPECIAL_CODE_MODE', 'false').lower() == 'true'
CODE_TOOL_PATTERN = 'code_interpreter'
FN_CALL_TEMPLATE_WITH_CI = """# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tool_descs}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{{"name": <function-name>, "arguments": <args-json-object>}}
</tool_call>
For code parameters, use placeholders first, and then put the code within <code></code> XML tags, such as:
<tool_call>
{{"name": <function-name>, "arguments": {{"code": ""}}}}
<code>
Here is the code.
</code>
</tool_call>"""


# Mainly for removing incomplete special tokens when streaming the output
# This assumes that '<tool_call>\n{"name": "' is the special token for the NousFnCallPrompt
def remove_incomplete_special_tokens(text: str) -> str:
    if text in '<tool_call>\n{"name": "':
        text = ''
    return text


def _skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i] in ' \t\r\n':
        i += 1
    return i


def _scan_json_string(text: str, i: int) -> tuple[str, int]:
    """Read the JSON string starting at ``text[i] == '"'``.

    Returns the decoded value and the index just past the closing quote. An
    unterminated string (a stream cut mid-value) yields what has arrived.
    """
    i += 1
    out = []
    while i < len(text):
        ch = text[i]
        if ch == '\\' and i + 1 < len(text):
            escape = text[i + 1]
            out.append({'n': '\n', 't': '\t', 'r': '\r'}.get(escape, escape))
            i += 2
            continue
        if ch == '"':
            return ''.join(out), i + 1
        out.append(ch)
        i += 1
    return ''.join(out), i


def _scan_json_value_prefix(text: str) -> str:
    """Return the shortest balanced JSON object/array prefix of ``text``.

    Unlike a strict parse this tolerates a stream cut mid-value, which is the
    only reason a truncated tool call reaches :func:`extract_fn`.
    """
    text = text.strip()
    if not text or text[0] not in '{[':
        return text

    closers = {'{': '}', '[': ']'}
    stack: list[str] = []
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if escaped:
            escaped = False
            continue
        if ch == '\\' and in_string:
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in closers:
            stack.append(closers[ch])
        elif stack and ch == stack[-1]:
            stack.pop()
            if not stack:
                return text[:i + 1]
    return text


def extract_fn(text: str):
    """Best-effort recovery of a tool call from a (possibly truncated) payload.

    ``json5`` has already rejected the payload by the time this runs, so the
    structure is scanned directly instead of being matched against literal
    ``"name": "`` separators: that pattern silently drops any model output
    written without the spaces a pretty-printer emits, leaving an empty name
    that the caller cannot dispatch.
    """
    fn_name, fn_args = '', ''
    text = text.strip()
    i = _skip_ws(text, 0)

    # Locate "name" wherever it sits, then read its string value.
    while i < len(text):
        if text[i] != '"':
            i += 1
            continue
        key, end = _scan_json_string(text, i)
        i = _skip_ws(text, end)
        if i < len(text) and text[i] == ':':
            i = _skip_ws(text, i + 1)
            if key == 'name' and i < len(text) and text[i] == '"':
                fn_name, i = _scan_json_string(text, i)
                i = _skip_ws(text, i)
            elif i < len(text) and text[i] in '{["':
                # Skip a nested value without parsing it: only the arguments
                # payload is needed, and a truncated one must survive intact.
                i += _scan_json_value_prefix(text[i:]).__len__()
            else:
                i += 1
        else:
            i += 1

    k = text.find('"arguments"')
    if k > 0:
        k = _skip_ws(text, k + len('"arguments"'))
        if k < len(text) and text[k] == ':':
            fn_args = _scan_json_value_prefix(text[_skip_ws(text, k + 1):])
    return fn_name, fn_args
