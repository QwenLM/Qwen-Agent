# Copyright 2026 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

import json
from typing import Any, Dict, Optional

from qwen_agent.agent import Agent
from qwen_agent.tools import BaseTool, ToolCallDenied


class EchoTool(BaseTool):
    name = 'echo'
    description = 'Echo a value.'
    parameters = [{'name': 'value', 'type': 'string', 'required': True}]

    def call(self, params, **kwargs):
        return params


class RecordingHook:

    def __init__(self, deny=False):
        self.events = []
        self.deny = deny

    def before_tool_call(self, *, tool_name: str, tool_args, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self.events.append(('before', tool_name, tool_args, context['agent_name']))
        if self.deny:
            raise ToolCallDenied('tool call rejected by policy')
        return {'invocation_id': 'test-1'}

    def after_tool_call(self, *, tool_name: str, tool_args, result, context, metadata):
        self.events.append(('after', tool_name, tool_args, result, metadata['invocation_id']))

    def on_tool_error(self, *, tool_name: str, tool_args, error: Exception, context, metadata):
        self.events.append(('error', tool_name, tool_args, type(error).__name__))


class MinimalAgent(Agent):

    def _run(self, messages, lang='en', **kwargs):
        yield messages


def test_tool_lifecycle_hook_receives_arguments_result_and_metadata():
    hook = RecordingHook()
    agent = MinimalAgent(function_list=[EchoTool()], name='test-agent', tool_lifecycle_hooks=[hook])

    result = agent._call_tool('echo', {'value': 'hello'})

    assert json.loads(result) == {'value': 'hello'}
    assert hook.events == [
        ('before', 'echo', {'value': 'hello'}, 'test-agent'),
        ('after', 'echo', {'value': 'hello'}, {'value': 'hello'}, 'test-1'),
    ]


def test_tool_lifecycle_hook_can_reject_before_execution():
    hook = RecordingHook(deny=True)
    agent = MinimalAgent(function_list=[EchoTool()], tool_lifecycle_hooks=[hook])

    result = agent._call_tool('echo', {'value': 'hello'})

    assert result == 'tool call rejected by policy'
    assert hook.events == [
        ('before', 'echo', {'value': 'hello'}, None),
        ('error', 'echo', {'value': 'hello'}, 'ToolCallDenied'),
    ]
