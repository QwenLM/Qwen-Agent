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
import sys

sys.path.insert(0, os.path.abspath(os.path.join(__file__, '../../..')))  # noqa

from examples import assistant_prompt_ir  # noqa


def test_build_prompt_ir_instruction_contains_reviewable_ir_prompt_contract():
    instruction = assistant_prompt_ir.build_prompt_ir_instruction()

    assert 'PromptIR' in instruction
    assert 'PromptLang-style' in instruction
    assert 'semantic intermediate representation' in instruction
    assert 'Clarify' in instruction
    assert 'review' in instruction
    assert 'confirm the contract' in instruction
    assert 'constraints' in instruction
    assert 'acceptance tests' in instruction
    assert 'target code' in instruction


def test_build_prompt_ir_suggestions_stop_before_code_generation():
    suggestions = assistant_prompt_ir.build_prompt_ir_suggestions()

    assert suggestions
    assert all('PromptIR' in suggestion for suggestion in suggestions)
    assert 'Stop before writing code' in suggestions[0]
    assert all('generate Python code' not in suggestion for suggestion in suggestions)


def test_init_agent_service_uses_prompt_ir_prompt_without_required_tools(monkeypatch):
    monkeypatch.setenv('QWEN_AGENT_PROMPT_IR_MODEL', 'qwen-test-model')

    agent = assistant_prompt_ir.init_agent_service()

    assert agent.name == 'PromptIR Pattern Demo'
    assert agent.llm is not None
    assert agent.llm.model == 'qwen-test-model'
    assert 'PromptIR' in agent.system_message
    assert agent.function_map == {}
