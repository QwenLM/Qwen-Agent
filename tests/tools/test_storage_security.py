# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

from pathlib import Path

import pytest

from qwen_agent.tools import Storage


def test_storage_rejects_keys_outside_root(tmp_path: Path):
    root = tmp_path / 'storage'
    outside = tmp_path / 'outside.txt'
    tool = Storage({'storage_root_path': str(root)})

    with pytest.raises(ValueError, match='escapes the storage root'):
        tool.call({'operate': 'put', 'key': '../outside.txt', 'value': 'secret'})
    with pytest.raises(ValueError, match='escapes the storage root'):
        tool.get('../outside.txt')
    with pytest.raises(ValueError, match='escapes the storage root'):
        tool.delete('../outside.txt')
    with pytest.raises(ValueError, match='escapes the storage root'):
        tool.scan('../')

    assert not outside.exists()


def test_storage_keeps_normal_keys_inside_root(tmp_path: Path):
    root = tmp_path / 'storage'
    tool = Storage({'storage_root_path': str(root)})

    tool.call({'operate': 'put', 'key': '/notes/today.txt', 'value': 'hello'})

    assert (root / 'notes' / 'today.txt').read_text() == 'hello'
    assert tool.get('notes/today.txt') == 'hello'
    assert '/today.txt: hello' in tool.scan('notes')

