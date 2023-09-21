import requests
import tiktoken
from jieba import analyse


def read_file(path):
    f = open(path, 'r', encoding='utf-8')
    lines = f.readlines()
    return ''.join(lines)


def save_text_to_file(path, text):
    try:
        with open(path, 'w') as fp:
            fp.write(text)
        return 'SUCCESS'
    except Exception as ex:
        return ex


def count_tokens(text):
    encoding = tiktoken.get_encoding('cl100k_base')
    tokens = encoding.encode(text)
    return len(tokens)


def gen_rec(text):
    return 'text'


def get_html_content(url):
    response = requests.get(url)
    html_content = response.text
    return html_content


def send_msg(url, msg):
    return requests.post(url, params=msg)


def get_key_word(text):
    # _wordlist = jieba.lcut(text.strip())
    _wordlist = analyse.extract_tags(text)
    wordlist = []
    for x in _wordlist:
        if x not in [' ', '  ', '\t', '\n', '\\', 'is', 'are', '的', '吗', '是', '了', '怎么', '如何', '什么', '？', '?', '!']:
            wordlist.append(x)
    print('wordlist: ', wordlist)
    return wordlist


def get_last_one_line_context(text):
    lines = text.split('\n')
    n = len(lines)
    for i in range(n-1, -1, -1):
        if lines[i].strip():
            res = lines[i]
            break
    return res
