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

from unittest.mock import Mock

import pytest

from qwen_agent.agents.memo_assistant import MemoAssistant
from qwen_agent.llm.schema import ASSISTANT, FUNCTION, USER, FunctionCall, Message


@pytest.mark.parametrize(('arguments', 'expected_memory'), [
    ('{}', ''),
    ('[]', ''),
    ('{"operate":"put","key":"note"}', ''),
    ('{"operate":"put","key":["note"],"value":"tea"}', ''),
    ('{"operate":"put","key":"note","value":3}', ''),
    ('{"operate":"put","key":"note","value":"tea"}', 'note: tea'),
])
def test_memo_assistant_replays_storage_history(tmp_path, monkeypatch, arguments, expected_memory):
    monkeypatch.setattr('qwen_agent.tools.storage.DEFAULT_WORKSPACE', str(tmp_path))
    llm = Mock(model='mock-model', model_type='mock')
    llm.chat.side_effect = [
        iter([[
            Message(role=ASSISTANT,
                    content='',
                    function_call=FunctionCall(name='storage', arguments=arguments),
                    extra={'function_id': '1'})
        ]]),
        iter([[Message(role=ASSISTANT, content='First turn')]]),
        iter([[Message(role=ASSISTANT, content='Next turn')]]),
    ]
    agent = MemoAssistant(llm=llm)
    first_user_message = Message(role=USER, content='Remember this preference.')
    first_turn = list(agent.run([first_user_message]))[-1]
    assert first_turn[1].role == FUNCTION
    if expected_memory:
        assert first_turn[1].content == 'Successfully saved note.'
    else:
        assert 'An error occurred when calling tool `storage`:' in first_turn[1].content

    second_user_message = Message(role=USER, content='What do you remember?')
    second_turn = list(agent.run([first_user_message, *first_turn, second_user_message]))

    assert second_turn[-1][-1].content == 'Next turn'
    system_prompt = llm.chat.call_args.kwargs['messages'][0].content
    assert f'<info>\n{expected_memory}\n</info>' in system_prompt
