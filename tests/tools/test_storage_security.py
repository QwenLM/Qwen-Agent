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


@pytest.mark.parametrize('operate', ['put', 'get', 'delete', 'scan'])
def test_storage_rejects_symlink_escape(tmp_path: Path, operate: str):
    root = tmp_path / 'storage'
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'secret.txt').write_text('secret')
    tool = Storage({'storage_root_path': str(root)})
    (root / 'link').symlink_to(outside, target_is_directory=True)
    key = 'link' if operate == 'scan' else 'link/secret.txt'
    with pytest.raises(ValueError, match='escapes the storage root'):
        tool.call({'operate': operate, 'key': key, 'value': 'changed'})
    assert (outside / 'secret.txt').read_text() == 'secret'


def test_storage_scan_rejects_external_symlink_file(tmp_path: Path):
    root = tmp_path / 'storage'
    outside = tmp_path / 'secret.txt'
    outside.write_text('secret')
    tool = Storage({'storage_root_path': str(root)})
    (root / 'link.txt').symlink_to(outside)
    with pytest.raises(ValueError, match='escapes the storage root'):
        tool.scan('')


def test_storage_scan_accepts_internal_symlink_file(tmp_path: Path):
    root = tmp_path / 'storage'
    tool = Storage({'storage_root_path': str(root)})
    tool.put('notes.txt', 'hello')
    (root / 'link.txt').symlink_to(root / 'notes.txt')
    assert '/link.txt: hello' in tool.scan('')
