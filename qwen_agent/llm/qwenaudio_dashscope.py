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
from qwen_agent.llm.qwenvl_dashscope import QwenVLChatAtDS


@register_llm('qwenaudio_dashscope')
class QwenAudioChatAtDS(QwenVLChatAtDS):

    @property
    def support_multimodal_input(self) -> bool:
        return True

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.model = self.model or 'qwen-audio-turbo-latest'
