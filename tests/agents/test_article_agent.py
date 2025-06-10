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

import pytest

from qwen_agent.agents import ArticleAgent


@pytest.mark.skip()
def test_article_agent_full_article():
    llm_cfg = {'model': 'qwen-max', 'api_key': '', 'model_server': 'dashscope'}
    agent = ArticleAgent(llm=llm_cfg)
    messages = [{
        'role': 'user',
        'content': [{
            'text': 'Qwen-Agent简介'
        }, {
            'file': 'https://github.com/QwenLM/Qwen-Agent'
        }]
    }]
    *_, last = agent.run(messages, full_article=True)

    assert last[-2]['content'] == '>\n> Writing Text: \n'
    assert len(last[-1]['content']) > 0
