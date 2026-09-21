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
from qwen_agent.tools.storage import UnsafeKeyError

SECRET = 'do not touch me'


def _make_tool(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'secret.txt').write_text(SECRET, encoding='utf-8')
    return Storage(cfg={'storage_root_path': str(tmp_path / 'storage_root')}), outside


@pytest.mark.parametrize('operate', ['put', 'get', 'delete', 'scan'])
def test_storage_rejects_relative_traversal_key(tmp_path, operate):
    tool, outside = _make_tool(tmp_path)
    target = outside if operate == 'scan' else outside / 'secret.txt'
    key = os.path.relpath(str(target), tool.root)
    assert key.startswith('..')

    params = {'operate': operate, 'key': key}
    if operate == 'put':
        params['value'] = 'pwned'
    with pytest.raises(UnsafeKeyError):
        tool.call(params)

    assert (outside / 'secret.txt').read_text(encoding='utf-8') == SECRET


@pytest.mark.parametrize('operate', ['put', 'get', 'delete', 'scan'])
def test_storage_rejects_absolute_key(tmp_path, operate):
    # `call` only strips one leading '/', so a doubled slash still leaves an
    # absolute path, which `os.path.join` would resolve outside of the root.
    tool, outside = _make_tool(tmp_path)
    target = outside if operate == 'scan' else outside / 'secret.txt'
    key = '/' + str(target)

    params = {'operate': operate, 'key': key}
    if operate == 'put':
        params['value'] = 'pwned'
    with pytest.raises(UnsafeKeyError):
        tool.call(params)

    assert (outside / 'secret.txt').read_text(encoding='utf-8') == SECRET


def test_storage_still_serves_normal_keys(tmp_path):
    tool, _ = _make_tool(tmp_path)
    assert tool.call({'operate': 'put', 'key': '345/456/11', 'value': 'hello'}) == 'Successfully saved 345/456/11.'
    assert tool.call({'operate': 'put', 'key': '/345/456/12', 'value': 'world'}) == 'Successfully saved 345/456/12.'
    assert tool.call({'operate': 'get', 'key': '345/456/11'}) == 'hello'
    assert sorted(tool.call({'operate': 'scan', 'key': '/345/456'}).split('\n')) == ['/11: hello', '/12: world']
    assert tool.call({'operate': 'delete', 'key': '345/456/11'}) == 'Successfully deleted 345/456/11'
