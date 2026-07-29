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

import pytest

from qwen_agent.tools import XquikTweetSearch
from qwen_agent.tools.xquik_tweet_search import XQUIK_API_CONTRACT, XQUIK_TWEET_SEARCH_PATH


class MockResponse:

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_xquik_tweet_search_requests_normalized_contract(monkeypatch):
    calls = []
    payload = {
        'tweets': [{
            'id': '123',
            'text': 'Qwen-Agent with X search',
            'created': 1782648000,
            'url': 'https://x.com/qwen/status/123',
            'lang': 'en',
            'like_count': 7,
            'bookmark_count': 2,
            'author': {
                'id': '456',
                'username': 'qwen',
                'name': 'Qwen',
            },
        }],
        'has_more': True,
        'next_cursor': 'cursor-2',
    }

    def mock_get(url, headers, params, timeout):
        calls.append({
            'url': url,
            'headers': headers,
            'params': params,
            'timeout': timeout,
        })
        return MockResponse(payload)

    monkeypatch.setattr('qwen_agent.tools.xquik_tweet_search.requests.get', mock_get)
    tool = XquikTweetSearch({
        'api_key': 'test-key',
        'base_url': 'https://example.com/',
        'timeout': 10,
    })

    result = json.loads(
        tool.call({
            'query': ' agent framework ',
            'query_type': 'Latest',
            'limit': 5,
            'cursor': 'cursor-1',
            'since_time': 1782600000,
            'until_time': 1782686400,
        }))

    assert calls == [{
        'url': f'https://example.com{XQUIK_TWEET_SEARCH_PATH}',
        'headers': {
            'Accept': 'application/json',
            'x-api-key': 'test-key',
            'xquik-api-contract': XQUIK_API_CONTRACT,
        },
        'params': {
            'q': 'agent framework',
            'queryType': 'Latest',
            'limit': 5,
            'cursor': 'cursor-1',
            'sinceTime': 1782600000,
            'untilTime': 1782686400,
        },
        'timeout': 10,
    }]
    assert result == payload


def test_xquik_tweet_search_requires_api_key(monkeypatch):
    monkeypatch.delenv('XQUIK_API_KEY', raising=False)
    tool = XquikTweetSearch()

    with pytest.raises(ValueError, match='XQUIK_API_KEY'):
        tool.call({'query': 'agent framework'})


def test_xquik_tweet_search_rejects_empty_query():
    tool = XquikTweetSearch({'api_key': 'test-key'})

    with pytest.raises(ValueError, match='query must not be empty'):
        tool.call({'query': ' '})


@pytest.mark.parametrize(
    'payload',
    [
        [],
        {
            'tweets': [],
            'has_more': 'yes',
            'next_cursor': '',
        },
        {
            'tweets': [],
            'has_more': False,
        },
    ],
)
def test_xquik_tweet_search_rejects_unexpected_response(payload, monkeypatch):
    monkeypatch.setattr(
        'qwen_agent.tools.xquik_tweet_search.requests.get',
        lambda *args, **kwargs: MockResponse(payload),
    )
    tool = XquikTweetSearch({'api_key': 'test-key'})

    with pytest.raises(ValueError, match='unexpected response contract'):
        tool.call({'query': 'agent framework'})


@pytest.mark.parametrize('timeout', [0, -1, True, '30'])
def test_xquik_tweet_search_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError, match='timeout must be a positive number'):
        XquikTweetSearch({'api_key': 'test-key', 'timeout': timeout})
