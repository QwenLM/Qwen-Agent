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

from typing import Union

from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.tools.simple_doc_parser import SimpleDocParser


@register_tool('web_extractor')
class WebExtractor(BaseTool):
    description = 'Get content of one webpage.'
    parameters = {
        'type': 'object',
        'properties': {
            'url': {
                'description': 'The webpage url.',
                'type': 'string',
            }
        },
        'required': ['url'],
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        url = params['url']
        parsed_web = SimpleDocParser().call({'url': url})
        return parsed_web
