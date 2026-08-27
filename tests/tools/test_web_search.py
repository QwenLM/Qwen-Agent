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

from unittest.mock import patch

from qwen_agent.tools import web_search


def test_web_search_request_has_timeout():
    with patch.object(web_search, 'SERPER_API_KEY', 'test-key'):
        with patch.object(web_search.requests, 'post') as post:
            post.return_value.json.return_value = {'organic': []}

            assert web_search.WebSearch.search('agent') == []

            post.assert_called_once_with(
                web_search.SERPER_URL,
                json={'q': 'agent'},
                headers={'Content-Type': 'application/json', 'X-API-KEY': 'test-key'},
                timeout=web_search.SERPER_TIMEOUT,
            )
