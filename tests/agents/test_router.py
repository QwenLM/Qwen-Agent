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

from qwen_agent.agents import Assistant, Router
from qwen_agent.llm.schema import ContentItem, FunctionCall, Message
from qwen_agent.tools.base import BaseTool


class DummyTool(BaseTool):
    name = 'dummy_tool'
    description = 'A dummy tool for tests.'

    def call(self, params, **kwargs):
        return 'dummy-result'


class FakeLLM:
    """Minimal LLM stub that records chat() calls and returns scripted replies."""

    def __init__(self, replies):
        self.model = 'fake-llm'
        self.model_type = 'fake'
        self.calls = []
        self._replies = list(replies)

    def chat(self, messages, functions=None, stream=True, extra_generate_cfg=None, **kwargs):
        self.calls.append({'functions': functions})
        reply = self._replies.pop(0)
        if stream:
            yield reply
        else:
            return reply


def test_router():
    llm_cfg = {'model': 'qwen-max'}
    llm_cfg_vl = {'model': 'qwen-vl-max'}
    tools = ['amap_weather']

    # Define a vl agent
    bot_vl = Assistant(llm=llm_cfg_vl, name='多模态助手', description='可以理解图像内容。')

    # Define a tool agent
    bot_tool = Assistant(
        llm=llm_cfg,
        name='天气预报助手',
        description='可以查询天气',
        function_list=tools,
    )

    # define a router (Simultaneously serving as a text agent)
    bot = Router(llm=llm_cfg, agents=[bot_vl, bot_tool])
    messages = [
        Message('user', [
            ContentItem(text='描述图片'),
            ContentItem(image='https://dashscope.oss-cn-beijing.aliyuncs.com/images/dog_and_girl.jpeg'),
        ])
    ]

    *_, last = bot.run(messages)
    assert isinstance(last[-1].content, str)

    messages = [Message('user', '海淀区天气')]

    *_, last = bot.run(messages)
    assert last[-3].function_call.name == 'amap_weather'
    assert last[-3].function_call.arguments == '{"location": "海淀区"}'
    assert last[-2].name == 'amap_weather'
    assert len(last[-1].content) > 0


def test_router_direct_reply_with_function_list():
    router_llm = FakeLLM([[Message(role='assistant', content='Hello!')]])
    child_llm = FakeLLM([[Message(role='assistant', content='child should not be called')]])
    child = Assistant(llm=child_llm, name='weather_agent', description='query weather')
    bot = Router(llm=router_llm, agents=[child], function_list=[DummyTool()])

    *_, last = bot.run([Message('user', 'hi')])

    assert not router_llm.calls[0]['functions']
    assert not child_llm.calls
    assert last[-1].content == 'Hello!'
    assert all(msg.role != 'function' for msg in last)


def test_router_function_list_does_not_pass_tools_on_routing_turn():
    router_llm = FakeLLM([[Message(role='assistant', content='Call: weather_agent')]])
    child_llm = FakeLLM([[Message(role='assistant', content='Sunny in Beijing')]])
    child = Assistant(llm=child_llm,
                      name='weather_agent',
                      description='query weather',
                      function_list=[DummyTool()])
    bot = Router(llm=router_llm, agents=[child], function_list=[DummyTool()])

    *_, last = bot.run([Message('user', 'what is the weather in Beijing?')])

    assert router_llm.calls, 'Router should call the LLM once for routing'
    assert not router_llm.calls[0]['functions']
    assert last[-1].content == 'Sunny in Beijing'
    assert last[-1].name == 'weather_agent'
    assert all('does not exists' not in (msg.content or '') for msg in last)


def test_router_function_list_does_not_execute_hallucinated_tools():
    router_llm = FakeLLM([[
        Message(role='assistant',
                content='',
                function_call=FunctionCall(name='invented_tool', arguments='{}'),
                extra={})
    ]])
    child_llm = FakeLLM([[Message(role='assistant', content='child should not be called')]])
    child = Assistant(llm=child_llm,
                      name='weather_agent',
                      description='query weather',
                      function_list=[DummyTool()])
    bot = Router(llm=router_llm, agents=[child], function_list=[DummyTool()])

    *_, last = bot.run([Message('user', 'what is the weather in Beijing?')])

    assert not router_llm.calls[0]['functions']
    assert not child_llm.calls
    assert all(msg.role != 'function' for msg in last)
    assert all('does not exists' not in (msg.content or '') for msg in last)


def test_router_still_lets_child_agent_use_tools():
    router_llm = FakeLLM([[Message(role='assistant', content='Call: weather_agent')]])
    child_llm = FakeLLM([
        [
            Message(role='assistant',
                    content='',
                    function_call=FunctionCall(name='dummy_tool', arguments='{}'),
                    extra={})
        ],
        [Message(role='assistant', content='Sunny in Beijing')],
    ])
    child = Assistant(llm=child_llm,
                      name='weather_agent',
                      description='query weather',
                      function_list=[DummyTool()])
    bot = Router(llm=router_llm, agents=[child], function_list=[DummyTool()])

    *_, last = bot.run([Message('user', 'what is the weather in Beijing?')])

    assert not router_llm.calls[0]['functions']
    assert child_llm.calls[0]['functions']
    assert any(msg.role == 'function' and msg.name == 'dummy_tool' for msg in last)
    assert last[-1].content == 'Sunny in Beijing'
    assert last[-1].name == 'weather_agent'
