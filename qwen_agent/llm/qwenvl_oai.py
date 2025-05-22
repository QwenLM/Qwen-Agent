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

import copy
import logging
import os
from pprint import pformat
from typing import List

from qwen_agent.llm import ModelServiceError
from qwen_agent.llm.base import register_llm
from qwen_agent.llm.oai import TextChatAtOAI
from qwen_agent.llm.schema import ContentItem, Message
from qwen_agent.log import logger
from qwen_agent.utils.utils import (encode_audio_as_base64, encode_image_as_base64, encode_video_as_base64)


@register_llm('qwenvl_oai')
class QwenVLChatAtOAI(TextChatAtOAI):

    @property
    def support_multimodal_input(self) -> bool:
        return True

    @staticmethod
    def convert_messages_to_dicts(messages: List[Message]) -> List[dict]:
        new_messages = []

        for msg in messages:
            content = msg.content
            if isinstance(content, str):
                content = [ContentItem(text=content)]
            assert isinstance(content, list)

            new_content = []
            for item in content:
                t, v = item.get_type_and_value()
                if t == 'text' and v:
                    new_content.append({'type': 'text', 'text': v})
                if t in ['image', 'video', 'audio']:
                    if isinstance(v, str):
                        v = conv_multimodel_value(t, v)
                    if isinstance(v, list):
                        new_v = []
                        for _v in v:
                            new_v.append(conv_multimodel_value(t, _v))
                        v = new_v
                    if isinstance(v, dict):
                        v['data'] = conv_multimodel_value(t, v['data'])

                    if t == 'image':
                        new_content.append({'type': 'image_url', 'image_url': {'url': v}})
                    elif t == 'video':
                        if isinstance(v, str):
                            new_content.append({'type': 'video_url', 'video_url': {'url': v}})
                        elif isinstance(v, list):
                            new_content.append({'type': 'video', 'video': v})
                        else:
                            raise TypeError
                    elif t == 'audio':
                        if isinstance(v, str):
                            new_content.append({'type': 'input_audio', 'input_audio': {'data': v}})
                        elif isinstance(v, dict):
                            new_content.append({'type': 'input_audio', 'input_audio': v})
                        else:
                            raise TypeError
                    else:
                        raise TypeError

            new_msg = msg.model_dump()
            new_msg['content'] = new_content
            new_messages.append(new_msg)

        if logger.isEnabledFor(logging.DEBUG):
            lite_messages = copy.deepcopy(new_messages)
            for msg in lite_messages:
                for item in msg['content']:
                    if item.get('image_url', {}).get('url', '').startswith('data:'):
                        item['image_url']['url'] = item['image_url']['url'][:64] + '...'
                    if item.get('video_url', {}).get('url', '').startswith('data:'):
                        item['video_url']['url'] = item['video_url']['url'][:64] + '...'
                    if item.get('input_audio', {}).get('data', '').startswith('data:'):
                        item['input_audio']['data'] = item['input_audio']['data'][:64] + '...'

            logger.debug(f'LLM Input:\n{pformat(lite_messages, indent=2)}')

        return new_messages


def conv_multimodel_value(t, v):
    if v.startswith('file://'):
        v = v[len('file://'):]
    if not v.startswith(('http://', 'https://', 'data:')):
        if os.path.exists(v):
            if t == 'image':
                v = encode_image_as_base64(v, max_short_side_length=1080)
            elif t == 'video':
                v = encode_video_as_base64(v)
            elif t == 'audio':
                v = encode_audio_as_base64(v)
            else:
                raise TypeError
        else:
            raise ModelServiceError(f'Local file "{v}" does not exist.')
    return v
