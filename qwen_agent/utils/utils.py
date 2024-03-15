import datetime
import hashlib
import json
import os
import re
import shutil
import socket
import sys
import traceback
import urllib
from typing import Dict, List, Literal, Optional, Union
from urllib.parse import urlparse

import jieba
import json5
import requests
from jieba import analyse

from qwen_agent.log import logger


def get_local_ip():
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


def hash_sha256(key):
    hash_object = hashlib.sha256(key.encode())
    key = hash_object.hexdigest()
    return key


def print_traceback(is_error=True):
    if is_error:
        logger.error(''.join(traceback.format_exception(*sys.exc_info())))
    else:
        logger.warning(''.join(traceback.format_exception(*sys.exc_info())))


def has_chinese_chars(data) -> bool:
    text = f'{data}'
    return len(re.findall(r'[\u4e00-\u9fff]+', text)) > 0


def get_basename_from_url(url: str) -> str:
    basename = os.path.basename(urlparse(url).path)
    basename = urllib.parse.unquote(basename)
    return basename.strip()


def is_local_path(path):
    if path.startswith('https://') or path.startswith('http://'):
        return False
    return True


def save_url_to_local_work_dir(url, base_dir, new_name=''):
    if not new_name:
        new_name = get_basename_from_url(url)
    new_path = os.path.join(base_dir, new_name)
    if os.path.exists(new_path):
        os.remove(new_path)
    logger.info(f'download {url} to {new_path}')
    start_time = datetime.datetime.now()
    if is_local_path(url):
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
            raise ValueError(
                'Can not download this file. Please check your network or the file link.'
            )
    end_time = datetime.datetime.now()
    logger.info(f'Time: {str(end_time - start_time)}')
    return new_path


def is_image(filename):
    filename = filename.lower()
    for ext in ['jpg', 'jpeg', 'png', 'webp']:
        if filename.endswith(ext):
            return True
    return False


def get_current_date_str(
    lang: Literal['en', 'zh'] = 'en',
    hours_from_utc: Optional[int] = None,
) -> str:
    if hours_from_utc is None:
        cur_time = datetime.datetime.now()
    else:
        cur_time = datetime.datetime.utcnow() + datetime.timedelta(
            hours=hours_from_utc)
    if lang == 'en':
        date_str = 'Current date: ' + cur_time.strftime('%A, %B %d, %Y')
    elif lang == 'zh':
        cur_time = cur_time.timetuple()
        date_str = f'当前时间：{cur_time.tm_year}年{cur_time.tm_mon}月{cur_time.tm_mday}日，星期'
        date_str += ['一', '二', '三', '四', '五', '六', '日'][cur_time.tm_wday]
        date_str += '。'
    else:
        raise NotImplementedError
    return date_str


def save_text_to_file(path, text):
    with open(path, 'w', encoding='utf-8') as fp:
        fp.write(text)


def read_text_from_file(path):
    with open(path, 'r', encoding='utf-8') as file:
        file_content = file.read()
    return file_content


def contains_html_tags(text):
    pattern = r'<(p|span|div|li|html|script)[^>]*?'
    return bool(re.search(pattern, text))


def get_file_type(path):
    # This is a temporary plan
    if is_local_path(path):
        try:
            content = read_text_from_file(path)
        except Exception:
            print_traceback()
            return 'Unknown'

        if contains_html_tags(content):
            return 'html'
        else:
            return 'Unknown'
    else:
        headers = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(path, headers=headers)
        if response.status_code == 200:
            if contains_html_tags(response.text):
                return 'html'
            else:
                return 'Unknown'
        else:
            print_traceback()
            return 'Unknown'


ignore_words = [
    '', ' ', '\t', '\n', '\\', 'is', 'are', 'am', 'what', 'how', '的', '吗', '是',
    '了', '啊', '呢', '怎么', '如何', '什么', '？', '?', '！', '!', '“', '”', '‘', '’',
    "'", "'", '"', '"', ':', '：', '讲了', '描述', '讲', '说说', '讲讲', '介绍', '总结下',
    '总结一下', '文档', '文章', '文稿', '稿子', '论文', 'PDF', 'pdf', '这个', '这篇', '这', '我',
    '帮我', '那个', '下', '翻译'
]


def get_split_word(text):
    text = text.lower()
    _wordlist = jieba.lcut(text.strip())
    wordlist = []
    for x in _wordlist:
        if x in ignore_words:
            continue
        wordlist.append(x)
    return wordlist


def parse_keyword(text):
    try:
        res = json5.loads(text)
    except Exception:
        return get_split_word(text)

    # json format
    _wordlist = []
    try:
        if 'keywords_zh' in res and isinstance(res['keywords_zh'], list):
            _wordlist.extend([kw.lower() for kw in res['keywords_zh']])
        if 'keywords_en' in res and isinstance(res['keywords_en'], list):
            _wordlist.extend([kw.lower() for kw in res['keywords_en']])
        wordlist = []
        for x in _wordlist:
            if x in ignore_words:
                continue
            wordlist.append(x)
        wordlist.extend(get_split_word(res['text']))
        return wordlist
    except Exception:
        return get_split_word(text)


def get_key_word(text):
    text = text.lower()
    _wordlist = analyse.extract_tags(text)
    wordlist = []
    for x in _wordlist:
        if x in ignore_words:
            continue
        wordlist.append(x)
    return wordlist


def get_last_one_line_context(text):
    lines = text.split('\n')
    n = len(lines)
    res = ''
    for i in range(n - 1, -1, -1):
        if lines[i].strip():
            res = lines[i]
            break
    return res


def extract_urls(text):
    pattern = re.compile(r'https?://\S+')
    urls = re.findall(pattern, text)
    return urls


def extract_obs(text):
    k = text.rfind('\nObservation:')
    j = text.rfind('\nThought:')
    obs = text[k + len('\nObservation:'):j]
    return obs.strip()


def extract_code(text):
    # Match triple backtick blocks first
    triple_match = re.search(r'```[^\n]*\n(.+?)```', text, re.DOTALL)
    if triple_match:
        text = triple_match.group(1)
    else:
        try:
            text = json5.loads(text)['code']
        except Exception:
            print_traceback()
    # If no code blocks found, return original text
    return text


def parse_latest_plugin_call(text):
    plugin_name, plugin_args = '', ''
    i = text.rfind('\nAction:')
    j = text.rfind('\nAction Input:')
    k = text.rfind('\nObservation:')
    if 0 <= i < j:  # If the text has `Action` and `Action input`,
        if k < j:  # but does not contain `Observation`,
            # then it is likely that `Observation` is ommited by the LLM,
            # because the output text may have discarded the stop word.
            text = text.rstrip() + '\nObservation:'  # Add it back.
        k = text.rfind('\nObservation:')
        plugin_name = text[i + len('\nAction:'):j].strip()
        plugin_args = text[j + len('\nAction Input:'):k].strip()
        text = text[:k]
    return plugin_name, plugin_args, text


def get_function_description(function: Dict) -> str:
    """
    Text description of function
    """
    tool_desc_template = {
        'zh':
        '### {name_for_human}\n\n{name_for_model}: {description_for_model} 输入参数：{parameters} {args_format}',
        'en':
        '### {name_for_human}\n\n{name_for_model}: {description_for_model} Parameters：{parameters} {args_format}'
    }
    if has_chinese_chars(function):
        tool_desc = tool_desc_template['zh']
    else:
        tool_desc = tool_desc_template['en']

    name = function.get('name', None)
    name_for_human = function.get('name_for_human', name)
    name_for_model = function.get('name_for_model', name)
    assert name_for_human and name_for_model
    args_format = function.get('args_format', '')
    return tool_desc.format(name_for_human=name_for_human,
                            name_for_model=name_for_model,
                            description_for_model=function['description'],
                            parameters=json.dumps(function['parameters'],
                                                  ensure_ascii=False),
                            args_format=args_format).rstrip()


def format_knowledge_to_source_and_content(
        result: Union[str, List[dict]]) -> List[dict]:
    knowledge = []
    if isinstance(result, str):
        result = f'{result}'.strip()
        docs = json5.loads(result)
    else:
        docs = result
    try:
        _tmp_knowledge = []
        assert isinstance(docs, list)
        for doc in docs:
            url, snippets = doc['url'], doc['text']
            assert isinstance(snippets, list)
            for s in snippets:
                _tmp_knowledge.append({'source': f'[文件]({url})', 'content': s})
        knowledge.extend(_tmp_knowledge)
    except Exception:
        print_traceback()
        knowledge.append({'source': '上传的文档', 'content': result})
    return knowledge
