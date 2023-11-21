import re
import socket
import sys
import traceback
from pathlib import Path

import jieba
import json5
from jieba import analyse
from qwen_agent.utils.tokenization_qwen import QWenTokenizer

from qwen_agent.log import logger


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def print_traceback():
    logger.error(''.join(traceback.format_exception(*sys.exc_info())))


def has_chinese_chars(data) -> bool:
    text = f'{data}'
    return len(re.findall(r'[\u4e00-\u9fff]+', text)) > 0


def save_text_to_file(path, text):
    try:
        with open(path, 'w', encoding='utf-8') as fp:
            fp.write(text)
        return 'SUCCESS'
    except Exception as ex:
        print_traceback()
        return ex


tokenizer = QWenTokenizer(Path(__file__).resolve().parent / 'qwen.tiktoken')


def count_tokens(text):
    tokens = tokenizer.tokenize(text)
    return len(tokens)


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


def get_key_word(text):
    text = text.lower()
    _wordlist = analyse.extract_tags(text)
    wordlist = []
    for x in _wordlist:
        if x in ignore_words:
            continue
        wordlist.append(x)
    print('wordlist: ', wordlist)
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


# TODO: Say no to these ugly if statements.
def format_answer(text):
    action, action_input, output = parse_latest_plugin_call(text)
    if 'code_interpreter' in text:
        rsp = ''
        code = extract_code(action_input)
        rsp += ('\n```py\n' + code + '\n```\n')
        obs = extract_obs(text)
        if '![fig' in obs:
            rsp += obs
        return rsp
    elif 'image_gen' in text:
        # get url of FA
        # img_urls = URLExtract().find_urls(text.split("Final Answer:")[-1].strip())
        obs = text.split('Observation:')[-1].split('\nThought:')[0].strip()
        img_urls = []
        if obs:
            logger.info(repr(obs))
            try:
                obs = json5.loads(obs)
                img_urls.append(obs['image_url'])
            except Exception:
                print_traceback()
                img_urls = []
        if not img_urls:
            img_urls = extract_urls(text.split('Final Answer:')[-1].strip())
        logger.info(img_urls)
        rsp = ''
        for x in img_urls:
            rsp += '\n![picture](' + x.strip() + ')'
        return rsp
    else:
        return text.split('Final Answer:')[-1].strip()
