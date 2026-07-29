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

import qwen_agent.tools.web_search as web_search_module
from qwen_agent.tools.web_search import DEFAULT_WEB_SEARCH_TIMEOUT, WebSearch


class MockResponse:

    def raise_for_status(self):
        return None

    def json(self):
        return {'organic': [{'title': 'Qwen-Agent'}]}


def test_web_search_uses_bounded_timeout(monkeypatch):
    calls = []

    def mock_post(url, json, headers, timeout):
        calls.append({
            'url': url,
            'json': json,
            'headers': headers,
            'timeout': timeout,
        })
        return MockResponse()

    monkeypatch.setattr(web_search_module, 'SERPER_API_KEY', 'test-key')
    monkeypatch.setattr(web_search_module.requests, 'post', mock_post)

    assert WebSearch.search('agent framework') == [{'title': 'Qwen-Agent'}]
    assert calls == [{
        'url': web_search_module.SERPER_URL,
        'json': {
            'q': 'agent framework',
        },
        'headers': {
            'Content-Type': 'application/json',
            'X-API-KEY': 'test-key',
        },
        'timeout': DEFAULT_WEB_SEARCH_TIMEOUT,
    }]
