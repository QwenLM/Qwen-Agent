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

from qwen_agent.agents.doc_qa import ParallelDocQA
from qwen_agent.agents.doc_qa.parallel_doc_qa_member import NO_RESPONSE


def test_is_none_response_recognises_the_marker():
    # NO_RESPONSE is '<None>'; the check lower-cased the model output but not
    # the marker, so the documented no-answer reply was kept as a real answer.
    qa = object.__new__(ParallelDocQA)

    assert qa._is_none_response(NO_RESPONSE)
    assert qa._is_none_response('<none>')
    assert qa._is_none_response('  <None>  ')
    assert qa._is_none_response('很抱歉，文档中没有相关信息')
    assert qa._is_none_response('{"res": "none"}')
    assert not qa._is_none_response('FastAPI 适合 IO 密集任务，因为它是异步框架。')


def test_parallel_qa():
    llm_cfg = {'model': 'qwen-max', 'api_key': '', 'model_server': 'dashscope'}
    agent = ParallelDocQA(llm=llm_cfg)
    messages = [{
        'role':
            'user',
        'content': [{
            'text': 'FastAPI适合IO密集任务吗'
        }, {
            'file': 'https://www.runoob.com/fastapi/fastapi-tutorial.html'
        }, {
            'file': 'https://www.runoob.com/fastapi/fastapi-install.html'
        }]
    }]
    *_, last = agent.run(messages)

    assert len(last[-1]['content']) > 0
