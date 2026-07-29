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
import os
from typing import Any, Dict, Optional, Union

import requests

from qwen_agent.tools.base import BaseTool, register_tool

DEFAULT_XQUIK_BASE_URL = 'https://xquik.com'
DEFAULT_XQUIK_TIMEOUT = 30
XQUIK_API_CONTRACT = '2026-04-29'
XQUIK_TWEET_SEARCH_PATH = '/api/v1/x/tweets/search'


@register_tool('xquik_tweet_search', allow_overwrite=True)
class XquikTweetSearch(BaseTool):
    name = 'xquik_tweet_search'
    description = 'Search public X posts through Xquik.'
    parameters = {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'Keyword, post ID, X status URL, or X search query.',
            },
            'query_type': {
                'type': 'string',
                'description': 'Return chronological Latest results or engagement-ranked Top results.',
                'enum': ['Latest', 'Top'],
            },
            'limit': {
                'type': 'integer',
                'description': 'Maximum number of posts to return.',
                'minimum': 1,
                'maximum': 200,
            },
            'cursor': {
                'type': 'string',
                'description': 'Opaque pagination cursor from a previous response.',
            },
            'since_time': {
                'type': 'integer',
                'description': 'Unix timestamp in seconds for the start of the search window.',
            },
            'until_time': {
                'type': 'integer',
                'description': 'Unix timestamp in seconds for the end of the search window.',
            },
        },
        'required': ['query'],
    }

    def __init__(self, cfg: Optional[Dict[str, Any]] = None):
        super().__init__(cfg)
        self.api_key = self.cfg.get('api_key') or os.getenv('XQUIK_API_KEY', '')
        self.base_url = (self.cfg.get('base_url') or os.getenv('XQUIK_BASE_URL', DEFAULT_XQUIK_BASE_URL)).rstrip('/')
        self.timeout = self.cfg.get('timeout', DEFAULT_XQUIK_TIMEOUT)
        if isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float)) or self.timeout <= 0:
            raise ValueError('timeout must be a positive number.')

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        query = params['query'].strip()
        if not query:
            raise ValueError('query must not be empty.')

        request_params: Dict[str, Any] = {'q': query}
        self._copy_optional_param(params, request_params, 'query_type', 'queryType')
        self._copy_optional_param(params, request_params, 'limit')
        self._copy_optional_param(params, request_params, 'cursor')
        self._copy_optional_param(params, request_params, 'since_time', 'sinceTime')
        self._copy_optional_param(params, request_params, 'until_time', 'untilTime')

        return self._format_response(self._get(request_params))

    @staticmethod
    def _copy_optional_param(source: dict, target: Dict[str, Any], source_key: str, target_key: Optional[str] = None):
        value = source.get(source_key)
        if value is not None and value != '':
            target[target_key or source_key] = value

    def _get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError('XQUIK_API_KEY is required to use xquik_tweet_search.')

        response = requests.get(
            f'{self.base_url}{XQUIK_TWEET_SEARCH_PATH}',
            headers={
                'Accept': 'application/json',
                'x-api-key': self.api_key,
                'xquik-api-contract': XQUIK_API_CONTRACT,
            },
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError('Xquik returned an unexpected response contract.')
        return payload

    @staticmethod
    def _format_response(response: Dict[str, Any]) -> str:
        if (not isinstance(response.get('tweets'), list) or not isinstance(response.get('has_more'), bool) or
                not isinstance(response.get('next_cursor'), str)):
            raise ValueError('Xquik returned an unexpected response contract.')
        return json.dumps(response, ensure_ascii=False)
