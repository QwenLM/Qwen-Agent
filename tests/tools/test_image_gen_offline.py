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
from unittest.mock import Mock

import pytest

from qwen_agent.llm.schema import ContentItem, Message
from qwen_agent.tools.image_gen import ImageGen


@pytest.mark.parametrize('json_params', [False, True])
@pytest.mark.parametrize('include_history', [False, True])
def test_image_gen_accepts_direct_calls(monkeypatch, json_params, include_history):
    expected = [ContentItem(image='https://example.invalid/generated.png')]
    model = Mock()
    model.chat.return_value = iter([[Message(role='assistant', content=expected)]])
    monkeypatch.setattr('qwen_agent.tools.image_gen.get_chat_model', lambda cfg: model)
    tool = ImageGen({'llm_cfg': {'model': 'offline-image-model'}})
    params = {'prompt': 'a dog'}
    kwargs = {'messages': [Message(role='user', content='earlier request')]} if include_history else {}

    result = tool.call(json.dumps(params) if json_params else params, **kwargs)

    assert result == expected
    messages = model.chat.call_args.kwargs['messages']
    assert messages == [Message(role='user', content=[ContentItem(text='a dog')])]
