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
from qwen_agent.memory import ConversationMemory, Memory


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


def test_conversation_memory():
    import shutil
    import tempfile

    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    try:
        mem = ConversationMemory(persist_dir=temp_dir, collection_name='test_conversations')

        # Test adding conversations
        messages1 = [
            Message(role='user', content='Hello, how are you?'),
            Message(role='assistant', content='I am fine, thank you!')
        ]
        mem.add_conversation(messages1)

        messages2 = [
            Message(role='user', content='What is the weather like?'),
            Message(role='assistant', content='It is sunny today.')
        ]
        mem.add_conversation(messages2)

        # Test retrieving relevant memories
        relevant = mem.retrieve_relevant('How are you?')
        assert len(relevant) > 0
        assert 'Hello' in ' '.join(relevant) or 'fine' in ' '.join(relevant)

        # Test persistence: create new instance and check if data persists
        mem2 = ConversationMemory(persist_dir=temp_dir, collection_name='test_conversations')
        relevant2 = mem2.retrieve_relevant('weather')
        assert len(relevant2) > 0
        assert 'sunny' in ' '.join(relevant2)

    finally:
        try:
            shutil.rmtree(temp_dir)
        except PermissionError:
            # ChromaDB may keep files open on Windows
            pass


if __name__ == '__main__':
    test_memory()
    test_conversation_memory()
