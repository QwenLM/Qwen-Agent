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
"""A PromptIR-style prompting pattern implemented with Assistant.

This example demonstrates a lightweight workflow inspired by
https://github.com/QwenLM/Qwen-Agent/issues/744: ask the model to first draft a
reviewable PromptLang-style semantic intermediate representation, then use the
reviewed representation to generate target code. The staged behavior is guided by
the system prompt and remains model-dependent; this is not a PromptIR parser,
validator, or compiler.
"""

import os

from qwen_agent.agents import Assistant
from qwen_agent.utils.output_beautify import typewriter_print

DEFAULT_PROMPT_IR_MODEL = 'qwen3-coder-480b-a35b-instruct'


def build_prompt_ir_instruction() -> str:
    return '''You are a PromptIR-style programming assistant.

PromptIR is a PromptLang-style semantic intermediate representation between
natural-language requirements and target code. For each programming request,
work in three stages:

1. Clarify intent and write a reviewable PromptIR contract. Include:
   - module or workflow name
   - inputs and outputs
   - types and constraints
   - preconditions and postconditions
   - side effects and permission boundaries
   - error handling and resource limits
   - acceptance tests
2. Present the PromptIR contract for review. Do not continue if important
   ambiguity remains; ask the user or reviewer to confirm the contract first.
3. After review, generate target code or tests from it. Keep the generated code
   faithful to the reviewed contract.

Do not skip the PromptIR stage. If the request is ambiguous, ask concise
clarifying questions before writing target code.'''


def build_prompt_ir_suggestions() -> list[str]:
    return [
        'Design a user registration flow as PromptIR with acceptance tests. Stop before writing code.',
        'Convert a leave approval requirement into PromptIR and acceptance tests.',
        'Write PromptIR for an order checkout workflow with inventory constraints.',
    ]


def init_agent_service():
    llm_cfg = {
        # Use QWEN_AGENT_PROMPT_IR_MODEL to try another DashScope chat model.
        'model': os.getenv('QWEN_AGENT_PROMPT_IR_MODEL', DEFAULT_PROMPT_IR_MODEL),
        'model_type': 'qwen_dashscope',
        'generate_cfg': {
            # Using the API's native tool call interface
            'use_raw_api': True,
        },
    }
    bot = Assistant(
        llm=llm_cfg,
        name='PromptIR Pattern Demo',
        description='Draft reviewable PromptIR before generating target code.',
        system_message=build_prompt_ir_instruction(),
    )

    return bot


def test(query: str = 'Design a small user registration module as PromptIR with acceptance tests.'):
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = [{'role': 'user', 'content': query}]
    response_plain_text = ''
    for response in bot.run(messages=messages):
        response_plain_text = typewriter_print(response, response_plain_text)


def app_tui():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []
    while True:
        query = input('user question: ')
        messages.append({'role': 'user', 'content': query})
        response = []
        response_plain_text = ''
        for response in bot.run(messages=messages):
            response_plain_text = typewriter_print(response, response_plain_text)
        messages.extend(response)


def app_gui():
    from qwen_agent.gui import WebUI

    # Define the agent
    bot = init_agent_service()
    chatbot_config = {'prompt.suggestions': build_prompt_ir_suggestions()}
    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
