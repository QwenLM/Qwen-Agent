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
"""Deterministic guard against fabricated tool results.

This example addresses a recurring failure mode (issue #737): during a tool call,
the model sometimes *fabricates the tool's result* inside its own generation and
then reasons on that invented result. The classic reproduction (from the #737
thread) is asking the agent to "generate a UUID using a tool": the model emits a
valid tool call and then, without waiting, continues with a made-up
``Observation: 550e8400-...`` — a value the tool never returned. When stop words
are ineffective (for example some non-OpenAI / vLLM deployments), that fabricated
observation can leak back into the reasoning loop and be treated as if it were a
real tool output, violating the plan/execution separation.

The core fix for the parsing/fallback path is being discussed on the issue itself.
This example is the *complementary, deterministic* half you can apply today: a
0-token, no-API-key guard that inspects the assistant's own text and flags any
tool-result-looking content the model wrote **before** the framework actually ran
the tool. It never guesses the right value — it only refuses to let an unearned
one through (fail closed), the same burden-of-proof stance used for citation
faithfulness in ``assistant_rag_with_citations.py``.

``detect_fabricated_tool_result`` returns, for a stretch of assistant-generated
text, the reasoning prefix that is safe to keep (the "Thought") and the fabricated
tail (any ``Observation:``/``Result:`` block the model invented). ``test()`` runs
the guard on planted cases fully offline; ``run_live()`` shows it wrapping a real
``Assistant`` over a tool and needs ``DASHSCOPE_API_KEY``.

The standalone, framework-agnostic lineage of this fail-closed detector (a verbatim
citation gate + burden-of-proof judge) lives at
https://github.com/Palo-Alto-AI-Research-Lab/verbatim-citation-gate .

Credit: issue #737 by @ydwasd; initial diagnosis ("the model does not stop after
issuing the tool call") by @tuhahaha; root-cause analysis of the parsing-failure
fallback by @delatorreAI.
"""
import re
from typing import List, Tuple

# Markers that, when they appear in *assistant-generated* text, indicate the model
# has started writing a tool result itself instead of waiting for the framework to
# run the tool and supply one. Matched case-insensitively at a line start.
_RESULT_MARKERS = (
    'observation',
    'result',
    'tool result',
    'tool_response',
    'function result',
    'output',
)

_MARKER_RE = re.compile(
    r'(?im)^\s*(?:' + '|'.join(re.escape(m) for m in _RESULT_MARKERS) + r')\s*[:：]',
)


def detect_fabricated_tool_result(assistant_text: str) -> Tuple[str, str]:
    """Split assistant text at the first fabricated tool-result marker.

    A model that has correctly *requested* a tool should stop; anything it writes
    after an ``Observation:`` / ``Result:`` style marker is content it invented
    rather than a value the tool returned. Returns ``(safe_prefix, fabricated_tail)``
    where ``fabricated_tail`` is empty when nothing was fabricated.

    This is deterministic and never fills in the "right" value: a fabricated tail is
    dropped so the framework can run the real tool, not silently trusted.
    """
    assistant_text = assistant_text or ''
    match = _MARKER_RE.search(assistant_text)
    if not match:
        return assistant_text, ''
    return assistant_text[:match.start()].rstrip(), assistant_text[match.start():].strip()


def guard_messages(messages: List[dict]) -> List[dict]:
    """Strip fabricated tool-result tails from assistant messages that also request a tool.

    Only touches an assistant turn that issues a tool/function call (or an
    ``Action:``): a plain assistant answer that happens to contain the word
    "Result:" is left alone. Returns a new list; inputs are not mutated.
    """
    guarded = []
    for msg in messages:
        is_assistant = msg.get('role') == 'assistant'
        requests_tool = bool(msg.get('function_call')) or ('\nAction:' in (msg.get('content') or ''))
        if is_assistant and requests_tool and msg.get('content'):
            safe, fabricated = detect_fabricated_tool_result(msg['content'])
            if fabricated:
                msg = {**msg, 'content': safe}
        guarded.append(msg)
    return guarded


def test():
    """Offline checks — no API key, no network."""
    # 1. Classic #737 repro: a tool call followed by a fabricated UUID observation.
    thought = 'Thought: I will call the UUID tool.\nAction: gen_uuid\nAction Input: {}'
    fabricated = thought + '\nObservation: 550e8400-e29b-41d4-a716-446655440000\nThought: The UUID is ready.'
    safe, tail = detect_fabricated_tool_result(fabricated)
    assert safe == thought, safe
    assert '550e8400' in tail, tail

    # 2. A clean tool request with no fabricated result is untouched.
    safe, tail = detect_fabricated_tool_result(thought)
    assert safe == thought and tail == '', (safe, tail)

    # 3. A plain assistant answer mentioning "result" is NOT a tool-requesting turn,
    #    so guard_messages leaves it alone.
    plain = [{'role': 'assistant', 'content': 'The result of the meeting was positive.'}]
    assert guard_messages(plain) == plain

    # 4. guard_messages strips the fabricated tail only from the tool-requesting turn.
    convo = [
        {'role': 'user', 'content': 'Generate a UUID using the tool.'},
        {'role': 'assistant', 'content': fabricated},
    ]
    guarded = guard_messages(convo)
    assert guarded[1]['content'] == thought, guarded[1]['content']
    assert 'Observation' not in guarded[1]['content']

    # 5. Fail-closed: a lone fabricated observation with no preceding thought yields an empty prefix.
    safe, tail = detect_fabricated_tool_result('Observation: 42')
    assert safe == '' and tail.startswith('Observation'), (safe, tail)

    print('All offline tool-result faithfulness checks passed.')


def run_live():
    """End-to-end demo over a real Assistant + tool. Needs DASHSCOPE_API_KEY."""
    import os

    if not os.getenv('DASHSCOPE_API_KEY'):
        print('Set DASHSCOPE_API_KEY to run the live demo; running offline test() instead.')
        return test()

    from qwen_agent.agents import Assistant
    from qwen_agent.tools.base import BaseTool, register_tool

    @register_tool('gen_uuid')
    class GenUuid(BaseTool):
        description = 'Generate a random UUID. Takes no arguments.'
        parameters = []

        def call(self, params: str, **kwargs) -> str:
            import uuid
            return str(uuid.uuid4())

    bot = Assistant(llm={'model': 'qwen-max'}, function_list=['gen_uuid'])
    messages = [{'role': 'user', 'content': 'Generate a UUID using the gen_uuid tool and tell me the value.'}]
    for response in bot.run(messages=messages):
        pass
    # Apply the deterministic guard to whatever the model produced this turn.
    guarded = guard_messages(response)
    for msg in guarded:
        print(f"[{msg.get('role')}] {str(msg.get('content'))[:200]}")


if __name__ == '__main__':
    test()
