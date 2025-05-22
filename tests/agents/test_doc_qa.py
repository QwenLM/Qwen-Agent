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

from qwen_agent.agents.doc_qa import BasicDocQA


def test_doc_qa():
    llm_cfg = {'model': 'qwen-max', 'api_key': '', 'model_server': 'dashscope'}
    agent = BasicDocQA(llm=llm_cfg)
    messages = [{
        'role': 'user',
        'content': [{
            'text': 'Summarize a title'
        }, {
            'file': 'https://www.runoob.com/fastapi/fastapi-tutorial.html'
        }]
    }]
    *_, last = agent.run(messages)

    assert len(last[-1]['content']) > 0
