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

from qwen_agent.agents import VirtualMemoryAgent


class FakeDelta:

    def __init__(self, content: str):
        self.content = content
        self.reasoning_content = None
        self.tool_calls = None


class FakeChoice:

    def __init__(self, content: str):
        self.delta = FakeDelta(content)


class FakeChunk:

    def __init__(self, contents):
        self.choices = [FakeChoice(c) for c in contents]


def _build_bot(chunks):
    bot = VirtualMemoryAgent(
        llm={
            'model': 'fake-model',
            'model_type': 'oai',
            'api_key': 'EMPTY',
            'model_server': 'http://127.0.0.1:1',
            'generate_cfg': {
                'max_retries': 0
            },
        })
    bot.llm._chat_complete_create = lambda *args, **kwargs: iter(chunks)
    return bot


def test_virtual_memory_agent_with_empty_llm_output():
    # The model service can answer with a stream that carries no message at all.
    bot = _build_bot([FakeChunk([])])
    responses = list(bot.run(messages=[{'role': 'user', 'content': 'hello'}]))
    assert len(responses) == 1  # emitted exactly once, not crashing and not duplicated
    assert responses[-1] == []
    assert bot.run_nonstream(messages=[{'role': 'user', 'content': 'hello'}]) == []


def test_virtual_memory_agent_with_normal_llm_output():
    bot = _build_bot([FakeChunk(['Hello!'])])
    responses = list(bot.run(messages=[{'role': 'user', 'content': 'hello'}]))
    # A successful non-tool run must emit its terminal response once, not twice.
    assert len(responses) == 1
    last = responses[-1]
    assert len(last) == 1
    assert last[-1]['role'] == 'assistant'
    assert last[-1]['content'] == 'Hello!'
    assert bot.run_nonstream(messages=[{'role': 'user', 'content': 'hello'}]) == last
