import datetime
import os
import re
from urllib.parse import unquote, urlparse

import add_qwen_libs  # NOQA
import jsonlines

from qwen_agent.utils.doc_parser import parse_html_bs, parse_pdf_pypdf
from qwen_agent.utils.utils import print_traceback, save_text_to_file
from qwen_server import server_config
from qwen_server.schema import Record


def is_local_path(path):
    if path.startswith('https://') or path.startswith('http://'):
        return False
    return True


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


def extract_and_cache_document(data, cache_file):
    print('Begin cache...')
    if data['url'][-4:] in ['.pdf', '.PDF']:
        date1 = datetime.datetime.now()

        # generate one processing record
        new_record = Record(url=data['url'],
                            time='',
                            type=data['type'],
                            raw=[],
                            extract='',
                            topic='',
                            checked=False,
                            session=[]).to_dict()
        with jsonlines.open(cache_file, mode='a') as writer:
            writer.write(new_record)

        if data['url'].startswith('https://') or data['url'].startswith(
                'http://'):
            pdf_path = data['url']
        else:
            parsed_url = urlparse(data['url'])
            print('parsed_url: ', parsed_url)
            pdf_path = unquote(parsed_url.path)
            pdf_path = sanitize_chrome_file_path(pdf_path)

        try:
            pdf_content = parse_pdf_pypdf(pdf_path)
        except Exception:
            print_traceback()
            # del the processing record
            lines = []
            if os.path.exists(cache_file):
                for line in jsonlines.open(cache_file):
                    if line['url'] != data['url']:
                        lines.append(line)
            with jsonlines.open(cache_file, mode='w') as writer:
                for new_line in lines:
                    writer.write(new_line)
            return 'failed'

        date2 = datetime.datetime.now()
        print('parse pdf time: ', date2 - date1)
        data['content'] = pdf_content
        data['type'] = 'pdf'
        extract = pdf_path.split('/')[-1].split('\\')[-1].split('.')[0]
    elif data['content'] and data['type'] == 'html':
        new_record = Record(url=data['url'],
                            time='',
                            type=data['type'],
                            raw=[],
                            extract='',
                            topic='',
                            checked=False,
                            session=[]).to_dict()
        with jsonlines.open(cache_file, mode='a') as writer:
            writer.write(new_record)

        try:
            tmp_html_file = os.path.join(server_config.cache_root, 'tmp.html')
            save_text_to_file(tmp_html_file, data['content'])
            data['content'] = parse_html_bs(tmp_html_file)
        except Exception:
            print_traceback()
        extract = data['content'][0]['metadata']['title']
    else:
        raise NotImplementedError

    today = datetime.date.today()
    new_record = Record(url=data['url'],
                        time=str(today),
                        type=data['type'],
                        raw=data['content'],
                        extract=extract,
                        topic='',
                        checked=True,
                        session=[])
    lines = []
    if os.path.exists(cache_file):
        for line in jsonlines.open(cache_file):
            if line['url'] != data['url']:
                lines.append(line)
    lines.append(new_record.to_dict())  # cache
    with jsonlines.open(cache_file, mode='w') as writer:
        for new_line in lines:
            writer.write(new_line)

    response = 'Cached'
    return response
