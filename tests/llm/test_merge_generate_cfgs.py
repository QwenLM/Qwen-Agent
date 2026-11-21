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

from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.function_calling import BaseFnCallModel
from qwen_agent.llm.schema import ASSISTANT, Message
from qwen_agent.utils.utils import merge_generate_cfgs, normalize_stop_words

REPLY = 'The answer is 42.'
STOP = 'Observation:'


class StubChatModel(BaseChatModel):
    """A chat model that returns a fixed reply without any network access."""

    def _chat_stream(self, messages, delta_stream=False, generate_cfg=None):
        yield [Message(role=ASSISTANT, content=REPLY)]

    def _chat_no_stream(self, messages, generate_cfg=None):
        return [Message(role=ASSISTANT, content=REPLY)]

    def _chat_with_functions(self, messages, functions, stream, delta_stream, generate_cfg, lang):
        return self._chat(messages, stream=stream, delta_stream=delta_stream, generate_cfg=generate_cfg)


class StubFnCallModel(BaseFnCallModel):
    """Minimal Qwen function-calling model, only used to exercise `__init__`."""

    def _chat_stream(self, messages, delta_stream=False, generate_cfg=None):
        yield [Message(role=ASSISTANT, content=REPLY)]

    def _chat_no_stream(self, messages, generate_cfg=None):
        return [Message(role=ASSISTANT, content=REPLY)]


def test_normalize_stop_words():
    assert normalize_stop_words(None) == []
    assert normalize_stop_words('') == []
    assert normalize_stop_words('Observation:') == ['Observation:']
    assert normalize_stop_words(['A', 'B']) == ['A', 'B']


def test_merge_generate_cfgs_normalizes_stop():
    assert merge_generate_cfgs({'stop': STOP}, {'stop': ['\nQuestion:']}) == {'stop': [STOP, '\nQuestion:']}
    assert merge_generate_cfgs({'stop': ['A']}, {'stop': 'BC'}) == {'stop': ['A', 'BC']}
    assert merge_generate_cfgs({'stop': 'AB'}, {'stop': 'CD'}) == {'stop': ['AB', 'CD']}
    assert merge_generate_cfgs({'stop': STOP}, None) == {'stop': [STOP]}
    assert merge_generate_cfgs({'stop': 'AB'}, {'stop': 'AB'}) == {'stop': ['AB']}


def test_string_stop_keeps_full_reply():
    # A single string stop describes one stop sequence, not one stop word per character.
    llm = StubChatModel(cfg={'model': 'stub', 'generate_cfg': {'stop': STOP}})
    responses = llm.chat([{'role': 'user', 'content': 'hi'}], stream=False)
    assert responses[-1]['content'] == REPLY

    llm = StubChatModel(cfg={'model': 'stub', 'generate_cfg': {'stop': STOP}})
    for responses in llm.chat([{'role': 'user', 'content': 'hi'}], stream=True):
        pass
    assert responses[-1]['content'] == REPLY


def test_qwen_fncall_model_accepts_string_stop():
    llm = StubFnCallModel({'model': 'stub', 'generate_cfg': {'fncall_prompt_type': 'qwen', 'stop': STOP}})
    assert llm.generate_cfg['stop'] == [STOP, '\u273fRESULT\u273f', '\u273fRETURN\u273f']
