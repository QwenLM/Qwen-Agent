import copy
import hashlib
import os
import re
import shutil
import signal
import socket
import sys
import time
import traceback
import urllib.parse
from typing import Any, List, Literal, Optional

import json5
import requests

from qwen_agent.llm.schema import ASSISTANT, FUNCTION, SYSTEM, USER, ContentItem, Message
from qwen_agent.log import logger


def append_signal_handler(sig, handler):
    """
    Installs a new signal handler while preserving any existing handler.
    If an existing handler is present, it will be called _after_ the new handler.
    """

    old_handler = signal.getsignal(sig)
    if not callable(old_handler):
        old_handler = None
        if sig == signal.SIGINT:

            def old_handler(*args, **kwargs):
                raise KeyboardInterrupt
        elif sig == signal.SIGTERM:

            def old_handler(*args, **kwargs):
                raise SystemExit

    def new_handler(*args, **kwargs):
        handler(*args, **kwargs)
        if old_handler is not None:
            old_handler(*args, **kwargs)

    signal.signal(sig, new_handler)


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def hash_sha256(text: str) -> str:
    hash_object = hashlib.sha256(text.encode())
    key = hash_object.hexdigest()
    return key


def print_traceback(is_error: bool = True):
    if is_error:
        logger.error(''.join(traceback.format_exception(*sys.exc_info())))
    else:
        logger.warning(''.join(traceback.format_exception(*sys.exc_info())))


def has_chinese_chars(data: Any) -> bool:
    text = f'{data}'
    return len(re.findall(r'[\u4e00-\u9fff]+', text)) > 0


def get_basename_from_url(path_or_url: str) -> str:
    if re.match(r'^[A-Za-z]:\\', path_or_url):
        # "C:\\a\\b\\c" -> "C:/a/b/c"
        path_or_url = path_or_url.replace('\\', '/')

    # "/mnt/a/b/c" -> "c"
    # "https://github.com/here?k=v" -> "here"
    # "https://github.com/" -> ""
    basename = urllib.parse.urlparse(path_or_url).path
    basename = os.path.basename(basename)
    basename = urllib.parse.unquote(basename)
    basename = basename.strip()

    # "https://github.com/" -> "" -> "github.com"
    if not basename:
        basename = [x.strip() for x in path_or_url.split('/') if x.strip()][-1]

    return basename


def is_http_url(path_or_url: str) -> bool:
    if path_or_url.startswith('https://') or path_or_url.startswith('http://'):
        return True
    return False


def is_image(path_or_url: str) -> bool:
    filename = get_basename_from_url(path_or_url).lower()
    for ext in ['jpg', 'jpeg', 'png', 'webp']:
        if filename.endswith(ext):
            return True
    return False


def save_url_to_local_work_dir(url: str, save_dir: str, save_filename: str = '') -> str:
    if not save_filename:
        save_filename = get_basename_from_url(url)
    new_path = os.path.join(save_dir, save_filename)
    if os.path.exists(new_path):
        os.remove(new_path)
    logger.info(f'Downloading {url} to {new_path}...')
    start_time = time.time()
    if not is_http_url(url):
        shutil.copy(url, new_path)
    else:
        headers = {
            'User-Agent':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            with open(new_path, 'wb') as file:
                file.write(response.content)
        else:
            raise ValueError('Can not download this file. Please check your network or the file link.')
    end_time = time.time()
    logger.info(f'Finished downloading {url} to {new_path}. Time spent: {end_time - start_time} seconds.')
    return new_path


def save_text_to_file(path: str, text: str) -> None:
    with open(path, 'w', encoding='utf-8') as fp:
        fp.write(text)


def read_text_from_file(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as file:
        file_content = file.read()
    return file_content


def contains_html_tags(text: str) -> bool:
    pattern = r'<(p|span|div|li|html|script)[^>]*?'
    return bool(re.search(pattern, text))


def get_file_type(path: str) -> Literal['pdf', 'docx', 'pptx', 'txt', 'html', 'unk']:
    f_type = get_basename_from_url(path).split('.')[-1].lower()
    if f_type in ['pdf', 'docx', 'pptx', 'txt']:
        # Specially supported file types
        return f_type

    if is_http_url(path):
        # Assuming that the URL is HTML by default
        return 'html'
    else:
        # Determine by reading local HTML file
        try:
            content = read_text_from_file(path)
        except Exception:
            print_traceback()
            return 'unk'

        if contains_html_tags(content):
            return 'html'
        else:
            return 'unk'


def extract_urls(text: str) -> List[str]:
    pattern = re.compile(r'https?://\S+')
    urls = re.findall(pattern, text)
    return urls


def extract_code(text: str) -> str:
    # Match triple backtick blocks first
    triple_match = re.search(r'```[^\n]*\n(.+?)```', text, re.DOTALL)
    if triple_match:
        text = triple_match.group(1)
    else:
        try:
            text = json5.loads(text)['code']
        except Exception:
            print_traceback(is_error=False)
    # If no code blocks found, return original text
    return text


def format_as_multimodal_message(msg: Message, add_upload_info: bool = True) -> Message:
    assert msg.role in (USER, ASSISTANT, SYSTEM, FUNCTION)
    content = []
    if isinstance(msg.content, str):  # if text content
        if msg.content:
            content = [ContentItem(text=msg.content)]
    elif isinstance(msg.content, list):  # if multimodal content
        files = []
        for item in msg.content:
            k, v = item.get_type_and_value()
            if k == 'text':
                content.append(ContentItem(text=v))
            if k == 'image':
                content.append(item)
            if k in ('file', 'image'):
                files.append(v)
        if add_upload_info and files and (msg.role in (SYSTEM, USER)):
            has_zh = has_chinese_chars(content)
            upload = []
            for f in [get_basename_from_url(f) for f in files]:
                if is_image(f):
                    if has_zh:
                        upload.append(f'![图片]({f})')
                    else:
                        upload.append(f'![image]({f})')
                else:
                    if has_zh:
                        upload.append(f'[文件]({f})')
                    else:
                        upload.append(f'[file]({f})')
            upload = ' '.join(upload)
            if has_zh:
                upload = f'（上传了 {upload}）\n\n'
            else:
                upload = f'(Uploaded {upload})\n\n'
            content = [ContentItem(text=upload)] + content
    else:
        raise TypeError
    msg = Message(
        role=msg.role,
        content=content,
        name=msg.name if msg.role == FUNCTION else None,
        function_call=msg.function_call,
    )
    return msg


def extract_text_from_message(msg: Message, add_upload_info: bool = True) -> str:
    if isinstance(msg.content, list):
        mm_msg = format_as_multimodal_message(msg, add_upload_info=add_upload_info)
        text = ''
        for item in mm_msg.content:
            if item.type == 'text':
                text += item.value
    elif isinstance(msg.content, str):
        text = msg.content
    else:
        raise TypeError
    return text.strip()


def extract_files_from_messages(messages: List[Message]) -> List[str]:
    files = []
    for msg in messages:
        if isinstance(msg.content, list):
            for item in msg.content:
                if item.file and item.file not in files:
                    files.append(item.file)
    return files


def merge_generate_cfgs(base_generate_cfg: Optional[dict], new_generate_cfg: Optional[dict]) -> dict:
    generate_cfg: dict = copy.deepcopy(base_generate_cfg or {})
    if new_generate_cfg:
        for k, v in new_generate_cfg.items():
            if k == 'stop':
                stop = generate_cfg.get('stop', [])
                stop = stop + [s for s in v if s not in stop]
                generate_cfg['stop'] = stop
            else:
                generate_cfg[k] = v
    return generate_cfg
