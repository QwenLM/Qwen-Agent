import os
from typing import Dict, Optional, Union

from qwen_agent.log import logger
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import (hash_sha256, print_traceback,
                                    read_text_from_file, save_text_to_file)


@register_tool('storage')
class Storage(BaseTool):
    """This is a special tool for data storage"""
    description = '数据在文件系统中存储和读取'
    parameters = [{
        'name': 'path',
        'type': 'string',
        'description': '数据存储的目录',
        'required': True
    }, {
        'name': 'operate',
        'type': 'string',
        'description':
        '数据操作类型，可选项为["put", "get", "delete", "scan"]之一，分别为存数据、取数据、删除数据、遍历数据',
        'required': True
    }, {
        'name': 'key',
        'type': 'string',
        'description': '数据的名称，是一份数据的唯一标识'
    }, {
        'name': 'value',
        'type': 'string',
        'description': '数据的内容，仅存数据时需要'
    }]

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.root = self.cfg.get('path', 'workspace/default_data_path')
        os.makedirs(self.root, exist_ok=True)
        self.data: Dict[str, Optional[str]] = {}
        # load all keys in this path
        for file in os.listdir(self.root):
            self.data[file] = None

    def call(self, params: Union[str, dict], **kwargs):

        params = self._verify_json_format_args(params)

        path = params['path']
        self.init(path)

        operate = params['operate']
        if operate == 'put':
            return self.put(params['key'], params['value'])
        elif operate == 'get':
            return self.get(params['key'])
        elif operate == 'delete':
            return self.delete(params['key'])
        else:
            return self.scan()

    def init(self, path: str):
        os.makedirs(path, exist_ok=True)
        self.root = path
        # load all keys
        self.data = {}
        for file in os.listdir(path):
            self.data[file] = None

    def put(self, key: str, value: str):
        # one file for one key value pair
        key = hash_sha256(key)

        msg = save_text_to_file(os.path.join(self.root, key), value)
        if msg == 'SUCCESS':
            self.data[key] = value
            return msg
        else:
            print_traceback()

    def get(self, key: str, re_load: bool = True):
        key = hash_sha256(key)
        if key in self.data and self.data[key] and (not re_load):
            return self.data[key]
        try:
            # lazy reading
            content = read_text_from_file(os.path.join(self.root, key))
            self.data[key] = content
            return content
        except Exception:
            return ''

    def delete(self, key):
        key = hash_sha256(key)
        try:
            if key in self.data:
                os.remove(os.path.join(self.root, key))
                self.data.pop(key)

            logger.info(f"Remove '{key}'")
        except OSError as ex:
            logger.error(f'Failed to remove: {ex}')

    def scan(self):
        for key in self.data.keys():
            yield [key, self.get(key)]
