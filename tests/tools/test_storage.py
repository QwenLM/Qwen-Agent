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

import pytest

from qwen_agent.tools import Storage


def test_storage_keeps_valid_keys_within_root(tmp_path):
    storage = Storage({'storage_root_path': str(tmp_path / 'storage')})

    storage.call({'operate': 'put', 'key': 'nested/value', 'value': 'hello'})
    storage.call({'operate': 'put', 'key': '/nested/other', 'value': 'world'})

    assert storage.call({'operate': 'get', 'key': 'nested/value'}) == 'hello'
    assert storage.call({'operate': 'get', 'key': '/nested/other'}) == 'world'


def test_storage_rejects_parent_path_for_all_operations(tmp_path):
    storage = Storage({'storage_root_path': str(tmp_path / 'storage')})
    outside_file = tmp_path / 'outside.txt'
    outside_dir = tmp_path / 'outside-dir'
    outside_file.write_text('secret', encoding='utf-8')
    outside_dir.mkdir()
    (outside_dir / 'secret.txt').write_text('secret', encoding='utf-8')

    calls = [
        {
            'operate': 'put',
            'key': '../created-outside.txt',
            'value': 'secret'
        },
        {
            'operate': 'get',
            'key': '../outside.txt'
        },
        {
            'operate': 'delete',
            'key': '../outside.txt'
        },
        {
            'operate': 'scan',
            'key': '../outside-dir'
        },
    ]
    for params in calls:
        with pytest.raises(ValueError, match='within storage root'):
            storage.call(params)

    assert outside_file.read_text(encoding='utf-8') == 'secret'
    assert (outside_dir / 'secret.txt').read_text(encoding='utf-8') == 'secret'
    assert not (tmp_path / 'created-outside.txt').exists()


def test_storage_rejects_direct_absolute_path(tmp_path):
    storage = Storage({'storage_root_path': str(tmp_path / 'storage')})

    with pytest.raises(ValueError, match='within storage root'):
        storage.put(str(tmp_path / 'outside.txt'), 'secret')


@pytest.mark.skipif(os.name != 'nt', reason='Windows-specific absolute path handling')
def test_storage_rejects_windows_absolute_path(tmp_path):
    storage = Storage({'storage_root_path': str(tmp_path / 'storage')})

    for key in (r'..\outside.txt', r'\outside.txt'):
        with pytest.raises(ValueError, match='within storage root'):
            storage.call({'operate': 'put', 'key': key, 'value': 'secret'})
