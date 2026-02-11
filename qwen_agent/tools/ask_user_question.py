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

import json
from typing import Union

from qwen_agent.tools.base import BaseTool, register_tool


@register_tool('ask_user_question')
class AskUserQuestion(BaseTool):
    """
    A tool that presents interactive questions to the user with multiple-choice options and optional freeform input.
    This tool creates a structured response that can be interpreted by the UI as an interactive element.
    """
    description = 'Present interactive questions to the user with multiple-choice options and optional freeform input field, and validate their responses.'
    parameters = {
        'type': 'object',
        'properties': {
            'question': {
                'type': 'string',
                'description': 'The question to ask the user'
            },
            'options': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'description': 'Array of options for the multiple choice question. Use "OTHER_OPTION" as a placeholder for a freeform input field.'
            },
            'correct_answer': {
                'type': 'string',
                'description': 'The correct answer among the options or expected format for freeform input'
            },
            'explanation': {
                'type': 'string',
                'description': 'Explanation for why the correct answer is correct'
            },
            'hint': {
                'type': 'string',
                'description': 'Optional hint to help the user answer the question'
            },
            'allow_freeform': {
                'type': 'boolean',
                'description': 'Whether to allow freeform input in addition to the options'
            }
        },
        'required': ['question', 'options'],
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        
        question = params.get('question', '')
        options = params.get('options', [])
        correct_answer = params.get('correct_answer', '')
        explanation = params.get('explanation', '')
        hint = params.get('hint', '')
        allow_freeform = params.get('allow_freeform', False)
        
        # Create a structured response that indicates this is an interactive element
        result = {
            'type': 'interactive_question',
            'question': question,
            'options': options,
            'correct_answer': correct_answer,
            'explanation': explanation,
            'hint': hint,
            'allow_freeform': allow_freeform,
            'status': 'presented',
            'message': f"Question: {question}\nOptions: {', '.join(options)}\nFreeform input allowed: {allow_freeform}"
        }
        
        return json.dumps(result, ensure_ascii=False)