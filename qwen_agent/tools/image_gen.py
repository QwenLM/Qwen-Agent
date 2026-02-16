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
from typing import Dict, List, Optional, Union

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import USER, ContentItem, Message
from qwen_agent.tools.base import BaseTool, register_tool


@register_tool('image_gen', allow_overwrite=True)
class ImageGen(BaseTool):
    description = 'An image generation service that takes text descriptions as input and returns a URL of the image.'  # noqa
    parameters = {
        'type': 'object',
        'properties': {
            'prompt': {
                'description':
                    'Detailed description of the desired content of the generated image. Please keep the specific requirements such as text from the original request fully intact. Omission is prohibited.',
                'type':
                    'string',
            }
        },
        'required': ['prompt'],
    }

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        llm_cfg = self.cfg.get('llm_cfg', {})
        if not llm_cfg:
            raise ValueError('llm_cfg is required!')
        self.llm = get_chat_model(llm_cfg)
        self.size = self.cfg.get('size', '1024*1024')

    def call(self, params: Union[str, dict], **kwargs) -> List[ContentItem]:
        if isinstance(params, str):
            params = json.loads(params)

        messages = [Message(role=USER, content=[ContentItem(text=params['prompt'])])]
        kwargs.pop('messages')

        *_, last = self.llm.chat(messages=messages)
        return last[-1]['content']
