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
            ContentItem(text='总结'),
            ContentItem(file='https://github.com/QwenLM/Qwen-Agent'),
            ContentItem(file=str(Path(__file__).resolve().parent.parent.parent / 'examples/resource/growing_girl.pdf'))
        ])
    ]
    *_, last = mem.run(messages)
    assert isinstance(last[-1].content, str)
    assert len(last[-1].content) > 0

    res = json5.loads(last[-1].content)
    assert isinstance(res, list)
