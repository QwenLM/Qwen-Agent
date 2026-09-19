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

from qwen_agent.agents.fncall_agent import FnCallAgent
from qwen_agent.llm.schema import ASSISTANT, FUNCTION, USER, FunctionCall, Message
from qwen_agent.tools.base import BaseTool


class RecordingTool(BaseTool):
    name = 'recording_tool'
    description = 'Record tool calls for tests.'
    parameters = []

    def __init__(self):
        super().__init__()
        self.calls = []

    def call(self, params, **kwargs):
        self.calls.append((params, kwargs))
        return 'tool executed'


def _build_agent(tool):
    agent = object.__new__(FnCallAgent)
    agent.function_map = {tool.name: tool}
    return agent


class ScriptedFnCallAgent(FnCallAgent):

    def __init__(self, tool):
        self.function_map = {tool.name: tool}
        self.system_message = None
        self.name = None
        self.description = None
        self._tool = tool

    def _call_llm(self, messages, **kwargs):
        if any(message.role == FUNCTION for message in messages):
            yield [Message(role=ASSISTANT, content='The tool call was not executed.')]
        else:
            yield [
                Message(role=ASSISTANT,
                        content='',
                        function_call=FunctionCall(name=self._tool.name, arguments='{}'),
                        extra={})
            ]


def test_tool_call_runs_without_approval_callback():
    tool = RecordingTool()
    agent = _build_agent(tool)

    result = agent._call_tool(tool.name, '{"value": 1}')

    assert result == 'tool executed'
    assert len(tool.calls) == 1


def test_tool_call_runs_when_approved():
    tool = RecordingTool()
    agent = _build_agent(tool)
    approval_requests = []

    def approve(tool_name, tool_args):
        approval_requests.append((tool_name, tool_args))
        return True

    result = agent._call_tool(tool.name, '{"value": 1}', tool_call_approval=approve)

    assert result == 'tool executed'
    assert approval_requests == [(tool.name, '{"value": 1}')]
    assert len(tool.calls) == 1
    assert tool.calls[0][1] == {}


def test_tool_call_is_not_executed_when_rejected():
    tool = RecordingTool()
    agent = _build_agent(tool)

    result = agent._call_tool(tool.name, '{}', tool_call_approval=lambda _name, _args: False)

    assert result == f'Tool call `{tool.name}` was rejected by the user.'
    assert tool.calls == []


def test_tool_call_is_not_executed_when_approval_callback_fails():
    tool = RecordingTool()
    agent = _build_agent(tool)

    def fail_approval(_tool_name, _tool_args):
        raise RuntimeError('approval service unavailable')

    result = agent._call_tool(tool.name, '{}', tool_call_approval=fail_approval)

    assert result == f'Tool call approval failed for `{tool.name}`: RuntimeError: approval service unavailable'
    assert tool.calls == []


def test_tool_call_is_not_executed_when_approval_callback_returns_non_bool():
    tool = RecordingTool()
    agent = _build_agent(tool)

    result = agent._call_tool(tool.name, '{}', tool_call_approval=lambda _name, _args: 'yes')

    assert result == f'Tool call approval failed for `{tool.name}`: callback must return a bool.'
    assert tool.calls == []


def test_rejection_is_returned_to_the_model_as_a_tool_result():
    tool = RecordingTool()
    agent = ScriptedFnCallAgent(tool)

    *_, response = agent.run([Message(role=USER, content='Run the tool.')],
                             tool_call_approval=lambda _name, _args: False)

    assert response[-2].role == FUNCTION
    assert response[-2].content == f'Tool call `{tool.name}` was rejected by the user.'
    assert response[-1].content == 'The tool call was not executed.'
    assert tool.calls == []
