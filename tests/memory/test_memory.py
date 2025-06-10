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

import os
import shutil
from pathlib import Path

import json5

from qwen_agent.llm.schema import ContentItem, Message
from qwen_agent.memory import Memory


def test_memory():
    if os.path.exists('workspace'):
        shutil.rmtree('workspace')

    llm_cfg = {'model': 'qwen-max'}
    mem = Memory(llm=llm_cfg)
    messages = [
        Message('user', [
            ContentItem(text='how to flip images'),
            ContentItem(file=str(Path(__file__).resolve().parent.parent.parent / 'examples/resource/doc.pdf'))
        ])
    ]
    *_, last = mem.run(messages, max_ref_token=4000, parser_page_size=500)
    print(last)
    assert isinstance(last[-1].content, str)
    assert len(last[-1].content) > 0

    res = json5.loads(last[-1].content)
    assert isinstance(res, list)


if __name__ == '__main__':
    test_memory()
