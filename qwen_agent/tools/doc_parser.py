import copy
import datetime
import json
import os
import re
from typing import Dict, List
from urllib.parse import unquote, urlparse

import json5
from pydantic import BaseModel

from qwen_agent.log import logger
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.tools.similarity_search import (RefMaterialInput,
                                                RefMaterialInputItem)
from qwen_agent.tools.storage import Storage
from qwen_agent.utils.doc_parser import parse_doc, parse_html_bs
from qwen_agent.utils.tokenization_qwen import count_tokens
from qwen_agent.utils.utils import print_traceback, save_text_to_file


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


def process_file(url: str, content: str, source: str, db: Storage = None):
    logger.info('Starting cache pages...')
    url = url
    if url.split('.')[-1].lower() in ['pdf', 'docx', 'pptx']:
        date1 = datetime.datetime.now()

        # generate one processing record
        db.put(url, '')

        if url.startswith('https://') or url.startswith('http://'):
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
            source = 'pdf'
            title = pdf_path.split('/')[-1].split('\\')[-1].split('.')[0]
        except Exception:
            print_traceback()
            # del the processing record
            db.delete(url)
            return 'failed'
    elif content and source == 'html':
        # generate one processing record
        db.put(url, '')

        try:
            tmp_html_file = os.path.join(db.root, 'tmp.html')
            save_text_to_file(tmp_html_file, content)
            content = parse_html_bs(tmp_html_file)
            title = content[0]['metadata']['title']
        except Exception:
            print_traceback()
            # del the processing record
            db.delete(url)
            return 'failed'
    else:
        logger.error(
            'Only Support the Following File Types: [\'.html\', \'.pdf\', \'.docx\', \'.pptx\']'
        )
        raise NotImplementedError

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

    meta_info = db.get('meta_info')
    if meta_info == 'Not Exist':
        meta_info = {}
    else:
        meta_info = json5.loads(meta_info)
    if isinstance(meta_info, list):
        logger.info('update meta_info to new format')
        new_meta_info = {}
        for x in meta_info:
            new_meta_info[x['url']] = x
        meta_info = new_meta_info

    meta_info[url] = {
        'url': url,
        'time': now_time,
        'title': title,
        'checked': True,
    }
    db.put('meta_info', json.dumps(meta_info, ensure_ascii=False))

    return new_record_str


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


def read_data_by_condition(db: Storage = None, **kwargs):
    """
    filter records from meta-data

    """
    meta_info = db.get('meta_info')
    if meta_info == 'Not Exist':
        records = []
    else:
        records = json5.loads(meta_info)
        records = records.values()

    if 'time_limit' in kwargs:
        filter_records = []
        for x in records:
            if kwargs['time_limit'][0] <= x['time'] <= kwargs['time_limit'][1]:
                filter_records.append(x)
        records = filter_records
    if 'checked' in kwargs:
        filter_records = []
        for x in records:
            if x['checked']:
                filter_records.append(x)
        records = filter_records

    return records


def format_records(records: List[Dict]):
    formatted_records = []
    for record in records:
        formatted_records.append(
            RefMaterialInput(url=record['url'],
                             text=[
                                 RefMaterialInputItem(
                                     content=x['page_content'],
                                     token=x['token']) for x in record['raw']
                             ]).to_dict())
    return formatted_records


@register_tool('doc_parser')
class DocParser(BaseTool):
    name = 'doc_parser'
    description = '解析文件'
    parameters = [{
        'name': 'url',
        'type': 'string',
        'description': '待解析的文件的路径'
    }]

    def call(self,
             params: str,
             db: Storage = None,
             raw: bool = False,
             **kwargs) -> str:
        params = self._verify_args(params)
        if isinstance(params, str):
            return 'Parameter Error'
        if not db:
            db = Storage()
            db.init('default_data_path')

        record = None
        if 'url' in params:
            record = db.get(params['url'])
            # need to parse and save doc
            if 'content' in kwargs:
                record = process_file(url=params['url'],
                                      content=kwargs['content'],
                                      source=kwargs['type'],
                                      db=db)

        if record is not None:
            records = [json5.loads(record)]
        else:
            # load records by conditions
            records = read_data_by_condition(db, **kwargs)
            if raw:
                return json.dumps(records, ensure_ascii=False)
            records = [
                json5.loads(db.get(record['url'])) for record in records
            ]

        formatted_records = format_records(records)
        return json.dumps(formatted_records, ensure_ascii=False)
