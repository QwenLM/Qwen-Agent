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

from typing import Dict, Optional

from qwen_agent.llm.base import register_llm
from qwen_agent.llm.qwenvl_oai import QwenVLChatAtOAI


@register_llm('qwenomni_oai')
class QwenOmniChatAtOAI(QwenVLChatAtOAI):

    @property
    def support_audio_input(self) -> bool:
        return True

    def __init__(self, cfg: Optional[Dict] = None):
        cfg = cfg or {}

        api_base = cfg.get('api_base')
        api_base = api_base or cfg.get('base_url')
        api_base = api_base or cfg.get('model_server')
        api_base = (api_base or '').strip()

        if not api_base:
            cfg['api_base'] = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

        super().__init__(cfg)
