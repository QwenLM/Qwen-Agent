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
import urllib.parse
from typing import Union

from qwen_agent.tools.base import BaseTool, register_tool


@register_tool('image_gen')
class ImageGen(BaseTool):
    description = 'An image generation service that takes text descriptions as input and returns a URL of the image. (The generated image URL should be described in markdown format in the reply to display the image: ![](URL_of_the_image))'
    parameters = {
        'type': 'object',
        'properties': {
            'prompt': {
                'description':
                    'Detailed description of the desired content of the generated image, such as details of characters, environment, actions, etc., in English.',
                'type':
                    'string',
            }
        },
        'required': ['prompt'],
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)

        prompt = params['prompt']
        prompt = urllib.parse.quote(prompt)
        return json.dumps({'image_url': f'https://image.pollinations.ai/prompt/{prompt}'}, ensure_ascii=False)
