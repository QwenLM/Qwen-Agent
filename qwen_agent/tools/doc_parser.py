import copy
import datetime
import json
import os
import re
from typing import Dict, Optional, Union
from urllib.parse import unquote, urlparse

import json5
from pydantic import BaseModel

from qwen_agent.log import logger
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.tools.storage import Storage
from qwen_agent.utils.doc_parser import parse_doc, parse_html_bs
from qwen_agent.utils.tokenization_qwen import count_tokens
from qwen_agent.utils.utils import (get_file_type, print_traceback,
                                    save_url_to_local_work_dir)


class FileTypeNotImplError(NotImplementedError):
    pass


class Record(BaseModel):
    url: str
    time: str
    source: str
    raw: list
    title: str
    topic: str
    checked: bool
    session: list

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'time': self.time,
            'source': self.source,
            'raw': self.raw,
            'title': self.title,
            'topic': self.topic,
            'checked': self.checked,
            'session': self.session
        }


def sanitize_chrome_file_path(file_path: str) -> str:
    # For Linux and macOS.
    if os.path.exists(file_path):
        return file_path

    # For native Windows, drop the leading '/' in '/C:/'
    win_path = file_path
    if win_path.startswith('/'):
        win_path = win_path[1:]
    if os.path.exists(win_path):
        return win_path

    # For Windows + WSL.
    if re.match(r'^[A-Za-z]:/', win_path):
        wsl_path = f'/mnt/{win_path[0].lower()}/{win_path[3:]}'
        if os.path.exists(wsl_path):
            return wsl_path

    # For native Windows, replace / with \.
    win_path = win_path.replace('/', '\\')
    if os.path.exists(win_path):
        return win_path

    return file_path


def process_file(url: str, db: Storage = None):
    logger.info('Starting cache pages...')
    url = url
    if url.split('.')[-1].lower() in ['pdf', 'docx', 'pptx']:
        date1 = datetime.datetime.now()

        if url.startswith('https://') or url.startswith('http://') or re.match(r'^[A-Za-z]:\\', win_path) or re.match(r'^[A-Za-z]:/', win_path):
            pdf_path = url
        else:
            parsed_url = urlparse(url)
            pdf_path = unquote(parsed_url.path)
            pdf_path = sanitize_chrome_file_path(pdf_path)

        try:
            pdf_content = parse_doc(pdf_path)
            date2 = datetime.datetime.now()
            logger.info('Parsing pdf time: ' + str(date2 - date1))
            content = pdf_content
            source = 'doc'
            title = pdf_path.split('/')[-1].split('\\')[-1].split('.')[0]
        except Exception:
            print_traceback()
            return 'failed'
    else:
        try:
            file_tmp_path = save_url_to_local_work_dir(url, db.root)
        except Exception:
            raise ValueError('Can not download this file')
        file_source = get_file_type(file_tmp_path)
        if file_source == 'html':
            try:
                content = parse_html_bs(file_tmp_path)
                title = content[0]['metadata']['title']
            except Exception:
                print_traceback()
                return 'failed'
            source = 'html'
        else:
            raise FileTypeNotImplError

    # save real data
    now_time = str(datetime.date.today())
    new_record = Record(url=url,
                        time=now_time,
                        source=source,
                        raw=content,
                        title=title,
                        topic='',
                        checked=True,
                        session=[]).to_dict()
    new_record_str = json.dumps(new_record, ensure_ascii=False)
    db.put(url, new_record_str)

    return new_record


def token_counter_backup(records):
    new_records = []
    for record in records:
        if not record['raw']:
            continue
        if 'token' not in record['raw'][0]['page_content']:
            tmp = []
            for page in record['raw']:
                new_page = copy.deepcopy(page)
                new_page['token'] = count_tokens(page['page_content'])
                tmp.append(new_page)
            record['raw'] = tmp
        new_records.append(record)
    return new_records


@register_tool('doc_parser')
class DocParser(BaseTool):
    description = '解析并存储一个文件，返回解析后的文件内容'
    parameters = [{
        'name': 'url',
        'type': 'string',
        'description': '待解析的文件的路径',
        'required': True
    }]

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.data_root = self.cfg.get(
            'path', 'workspace/default_doc_parser_data_path')
        self.db = Storage({'path': self.data_root})

    def call(self,
             params: Union[str, dict],
             ignore_cache: bool = False) -> dict:
        """
        Parse file by url, and return the formatted content

        :param params: The url of the file
        :param ignore_cache: When set to True, overwrite the same documents that have been parsed before.
        :return: The parsed file content
        """

        params = self._verify_json_format_args(params)

        record = self.db.get(params['url'])
        if record and not ignore_cache:
            record = json5.loads(record)
        else:
            # The url has not been parsed or ignore_cache: need to parse and save doc
            record = process_file(url=params['url'], db=self.db)
        return record
