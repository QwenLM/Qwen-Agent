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

import tempfile

from qwen_agent.tools import Storage
from qwen_agent.tools.storage import KeyNotExistsError


def _make_tool():
    tmp = tempfile.TemporaryDirectory()
    tool = Storage(cfg={'storage_root_path': tmp.name})
    return tmp, tool


def test_put_get_round_trip():
    tmp, tool = _make_tool()
    key = 'my_key'
    value = 'hello world'
    assert 'Successfully saved' in tool.call({'operate': 'put', 'key': key, 'value': value})
    assert tool.call({'operate': 'get', 'key': key}) == value
    tmp.cleanup()


def test_nested_key_round_trip():
    tmp, tool = _make_tool()
    key = 'folder/sub/name'
    value = 'nested value'
    tool.call({'operate': 'put', 'key': key, 'value': value})
    assert tool.call({'operate': 'get', 'key': key}) == value
    tmp.cleanup()


def test_get_missing_key_raises():
    tmp, tool = _make_tool()
    try:
        tool.call({'operate': 'get', 'key': 'does_not_exist'})
        assert False, 'expected KeyNotExistsError'
    except KeyNotExistsError:
        pass
    tmp.cleanup()


def test_delete_existing_and_missing():
    tmp, tool = _make_tool()
    key = 'k'
    tool.call({'operate': 'put', 'key': key, 'value': 'v'})
    assert 'Successfully deleted' in tool.call({'operate': 'delete', 'key': key})
    # After deletion, reading raises; deleting again reports failure.
    try:
        tool.call({'operate': 'get', 'key': key})
        assert False, 'expected KeyNotExistsError after delete'
    except KeyNotExistsError:
        pass
    assert 'Delete Failed' in tool.call({'operate': 'delete', 'key': key})
    tmp.cleanup()


def test_scan_folder_returns_all_keys():
    tmp, tool = _make_tool()
    tool.call({'operate': 'put', 'key': 'a/b', 'value': '1'})
    tool.call({'operate': 'put', 'key': 'a/c', 'value': '2'})
    out = tool.call({'operate': 'scan', 'key': 'a'})
    assert '/b: 1' in out
    assert '/c: 2' in out
    tmp.cleanup()


def test_scan_on_non_folder_fails():
    tmp, tool = _make_tool()
    tool.call({'operate': 'put', 'key': 'file', 'value': 'x'})
    assert 'Scan Failed' in tool.call({'operate': 'scan', 'key': 'file'})
    tmp.cleanup()


if __name__ == '__main__':
    test_put_get_round_trip()
    test_nested_key_round_trip()
    test_get_missing_key_raises()
    test_delete_existing_and_missing()
    test_scan_folder_returns_all_keys()
    test_scan_on_non_folder_fails()
    print('All storage tests passed.')
