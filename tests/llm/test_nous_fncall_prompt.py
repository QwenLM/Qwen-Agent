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

from qwen_agent.llm.fncall_prompts.nous_fncall_prompt import NousFnCallPrompt
from qwen_agent.llm.schema import ASSISTANT, USER, ContentItem, Message


def test_postprocess_keeps_tool_call_without_arguments():
    r"""A well-formed call to a zero-argument tool may omit "arguments";
    it must become a function_call message, not be silently dropped."""
    prompt = NousFnCallPrompt()
    messages = [
        Message(role=USER, content=[ContentItem(text='list the files please')]),
        Message(
            role=ASSISTANT,
            content=[ContentItem(text='Sure.\n<tool_call>\n{"name": "list_files"}\n</tool_call>')],
        ),
    ]

    out = prompt.postprocess_fncall_messages(messages)
    fn_calls = [m for m in out if m.function_call is not None]
    assert len(fn_calls) == 1
    assert fn_calls[0].function_call.name == 'list_files'
    assert fn_calls[0].function_call.arguments == '{}'


def test_postprocess_explicit_empty_arguments():
    r"""{"name": ..., "arguments": {}} keeps working as before."""
    prompt = NousFnCallPrompt()
    messages = [
        Message(
            role=ASSISTANT,
            content=[ContentItem(
                text='<tool_call>\n{"name": "ping", "arguments": {}}\n</tool_call>'
            )],
        ),
    ]

    out = prompt.postprocess_fncall_messages(messages)
    fn_calls = [m for m in out if m.function_call is not None]
    assert len(fn_calls) == 1
    assert fn_calls[0].function_call.name == 'ping'
    assert fn_calls[0].function_call.arguments == '{}'
