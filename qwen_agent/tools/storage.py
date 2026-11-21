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
from typing import Dict, Optional, Union

from qwen_agent.settings import DEFAULT_WORKSPACE
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import read_text_from_file, save_text_to_file


class KeyNotExistsError(ValueError):
    pass


@register_tool('storage')
class Storage(BaseTool):
    """
    This is a special tool for data storage
    """
    description = '存储和读取数据的工具'
    parameters = {
        'type': 'object',
        'properties': {
            'operate': {
                'description': '数据操作类型，可选项为["put", "get", "delete", "scan"]之一，分别为存数据、取数据、删除数据、遍历数据',
                'type': 'string',
            },
            'key': {
                'description': '数据的路径，类似于文件路径，是一份数据的唯一标识，不能为空，默认根目录为`/`。存数据时，应该合理的设计路径，保证路径含义清晰且唯一。',
                'type': 'string',
                'default': '/'
            },
            'value': {
                'description': '数据的内容，仅存数据时需要',
                'type': 'string',
            },
        },
        'required': ['operate'],
    }

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.root = self.cfg.get('storage_root_path', os.path.join(DEFAULT_WORKSPACE, 'tools', self.name))
        os.makedirs(self.root, exist_ok=True)

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        operate = params['operate']
        key = params.get('key', '/')
        if key.startswith('/'):
            key = key[1:]

        if operate == 'put':
            assert 'value' in params
            return self.put(key, params['value'])
        elif operate == 'get':
            return self.get(key)
        elif operate == 'delete':
            return self.delete(key)
        else:
            return self.scan(key)

    def _resolve_key_path(self, key: str, path: Optional[str] = None,
                          allow_root: bool = False) -> str:
        """Resolve a key to an absolute path inside the storage root.

        Keys come from the model, so they must not escape the storage root
        (e.g. ``../x`` or ``sub/../../x``) or name the root itself (the
        documented default key ``/`` ends up here after call() strips the
        leading slash). Windows-style separators are normalized so ``a\\b``
        nests like ``a/b`` instead of naming one file with a backslash.
        """
        path = path or self.root
        key = key.replace('\\', '/')
        if os.path.isabs(key):
            raise ValueError(
                f'Invalid key: {key} must be a relative path inside the storage root')
        full = os.path.realpath(os.path.join(path, key))
        root = os.path.realpath(path)
        if full == root:
            if allow_root:
                return full
            raise ValueError(
                'Invalid key: the key must name a file or folder inside the '
                'storage root, not the root itself')
        if not full.startswith(root + os.sep):
            raise ValueError(
                f'Invalid key: {key} escapes the storage root')
        return full

    def put(self, key: str, value: str, path: Optional[str] = None) -> str:
        full = self._resolve_key_path(key, path)

        # one file for one key value pair
        os.makedirs(os.path.dirname(full), exist_ok=True)

        save_text_to_file(full, value)
        return f'Successfully saved {key}.'

    def get(self, key: str, path: Optional[str] = None) -> str:
        full = self._resolve_key_path(key, path)
        if not os.path.isfile(full):
            raise KeyNotExistsError(f'Get Failed: {key} does not exist')
        return read_text_from_file(full)

    def delete(self, key, path: Optional[str] = None) -> str:
        full = self._resolve_key_path(key, path)
        if os.path.exists(full):
            if os.path.isdir(full):
                return f'Delete Failed: {key} is a folder, not a file'
            os.remove(full)
            return f'Successfully deleted {key}'
        else:
            return f'Delete Failed: {key} does not exist'

    def scan(self, key: str, path: Optional[str] = None) -> str:
        base = path or self.root
        full = self._resolve_key_path(key, path, allow_root=True)
        if os.path.exists(full):
            if not os.path.isdir(full):
                return 'Scan Failed: The scan operation requires passing in a folder path as the key.'
            # All key-value pairs. Keys are reported relative to the storage
            # root (not the scanned subfolder), so scanning "docs" returns
            # keys like "/docs/readme.txt" that put/get can consume.
            kvs = {}
            base_real = os.path.realpath(base)
            for root, dirs, files in os.walk(full):
                for file in files:
                    k = os.path.join(root, file)[len(base_real):]
                    k = k.replace('\\', '/')
                    if not k.startswith('/'):
                        k = '/' + k
                    v = read_text_from_file(os.path.join(root, file))
                    kvs[k] = v
            return '\n'.join([f'{k}: {v}' for k, v in kvs.items()])
        else:
            return f'Scan Failed: {key} does not exist.'
