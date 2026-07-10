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

import json

import pytest

from qwen_agent.llm.schema import ASSISTANT, DEFAULT_SYSTEM_MESSAGE, SYSTEM, USER, ContentItem, Message
from qwen_agent.utils.utils import (extract_code, extract_files_from_messages, extract_images_from_messages,
                                    extract_markdown_urls, extract_text_from_message, extract_urls,
                                    format_as_text_message, get_basename_from_url, get_file_type, get_last_usr_msg_idx,
                                    has_chinese_chars, has_chinese_messages, hash_sha256, is_http_url, is_image,
                                    json_dumps_compact, json_dumps_pretty, json_loads, merge_generate_cfgs,
                                    rm_default_system)


def test_hash_sha256():
    # Deterministic and matches the standard SHA-256 hex digest.
    assert hash_sha256('hello') == '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
    assert hash_sha256('hello') == hash_sha256('hello')
    assert hash_sha256('hello') != hash_sha256('world')


@pytest.mark.parametrize('data, expected', [
    ('hello world', False),
    ('你好，世界', True),
    ('mixed 中文 text', True),
    (123, False),
    (['英文', 'and', '中文'], True),
])
def test_has_chinese_chars(data, expected):
    assert has_chinese_chars(data) == expected


def test_has_chinese_messages():
    assert has_chinese_messages([{'role': 'user', 'content': '你好'}]) is True
    assert has_chinese_messages([{'role': 'user', 'content': 'hello'}]) is False
    assert has_chinese_messages([{'role': 'system', 'content': '你是一个助手'}]) is True
    # By default only the system and user roles are inspected.
    assert has_chinese_messages([{'role': 'assistant', 'content': '你好'}]) is False
    assert has_chinese_messages([{'role': 'assistant', 'content': '你好'}], check_roles=('assistant',)) is True


@pytest.mark.parametrize('path_or_url, expected', [
    ('https://example.com', True),
    ('http://example.com/a/b', True),
    ('/local/path/file.pdf', False),
    ('file.txt', False),
    ('ftp://example.com', False),
])
def test_is_http_url(path_or_url, expected):
    assert is_http_url(path_or_url) == expected


@pytest.mark.parametrize('path_or_url, expected', [
    ('https://github.com/here?k=v', 'here'),
    ('https://github.com/', 'github.com'),
    ('/mnt/a/b/c.pdf', 'c.pdf'),
    ('file.txt', 'file.txt'),
    ('https://arxiv.org/pdf/2310.08560.pdf', '2310.08560.pdf'),
])
def test_get_basename_from_url(path_or_url, expected):
    assert get_basename_from_url(path_or_url) == expected


@pytest.mark.parametrize('path_or_url, expected', [
    ('photo.jpg', True),
    ('photo.JPG', True),
    ('photo.jpeg', True),
    ('photo.PNG', True),
    ('https://example.com/img.webp', True),
    ('document.pdf', False),
    ('archive.zip', False),
])
def test_is_image(path_or_url, expected):
    assert is_image(path_or_url) == expected


@pytest.mark.parametrize('path, expected', [
    ('report.pdf', 'pdf'),
    ('slides.pptx', 'pptx'),
    ('paper.DOCX', 'docx'),
    ('data.csv', 'csv'),
    ('data.tsv', 'tsv'),
    ('sheet.xlsx', 'xlsx'),
    ('sheet.xls', 'xls'),
])
def test_get_file_type_by_extension(path, expected):
    # These extensions are resolved locally, without any network access.
    assert get_file_type(path) == expected


def test_extract_urls():
    assert extract_urls('see https://example.com and http://test.org/p here') == [
        'https://example.com', 'http://test.org/p'
    ]
    assert extract_urls('no urls in this text') == []


def test_extract_markdown_urls():
    md = '[link](https://a.com) and an image ![img](https://b.com/i.png)'
    assert extract_markdown_urls(md) == ['https://a.com', 'https://b.com/i.png']
    assert extract_markdown_urls('plain text without links') == []


def test_extract_code():
    assert extract_code('```python\nprint(1)\n```') == 'print(1)\n'
    assert extract_code('{"code": "x = 1"}') == 'x = 1'
    # Text without a code block or a "code" field is returned unchanged.
    assert extract_code('just some text') == 'just some text'


def test_json_loads():
    assert json_loads('{"a": 1}') == {'a': 1}
    # Fenced JSON code blocks are stripped before parsing.
    assert json_loads('```json\n{"a": 1}\n```') == {'a': 1}
    # Falls back to json5 for relaxed JSON (single quotes / trailing commas).
    assert json_loads("{a: 1, b: 'x',}") == {'a': 1, 'b': 'x'}
    with pytest.raises(json.decoder.JSONDecodeError):
        json_loads('this is not json')


def test_json_dumps():
    obj = {'a': 1, 'b': 2}
    assert json_dumps_compact(obj) == '{"a": 1, "b": 2}'
    assert json_dumps_pretty(obj) == '{\n  "a": 1,\n  "b": 2\n}'
    # Chinese characters are kept as-is by default (ensure_ascii=False).
    assert json_dumps_compact({'k': '中文'}) == '{"k": "中文"}'


def test_merge_generate_cfgs():
    # A missing base config is treated as an empty dict.
    assert merge_generate_cfgs(None, {'top_p': 0.5}) == {'top_p': 0.5}
    # New values override existing ones.
    assert merge_generate_cfgs({'top_p': 0.8}, {'top_p': 0.5, 'temperature': 0.1}) == {'top_p': 0.5, 'temperature': 0.1}
    # `stop` words are merged (deduplicated) rather than replaced.
    assert merge_generate_cfgs({'stop': ['a', 'b']}, {'stop': ['b', 'c']}) == {'stop': ['a', 'b', 'c']}
    # The base config must not be mutated.
    base = {'stop': ['a']}
    merge_generate_cfgs(base, {'stop': ['b']})
    assert base == {'stop': ['a']}


def test_get_last_usr_msg_idx():
    messages = [
        Message(SYSTEM, 'sys'),
        Message(USER, 'q1'),
        Message(ASSISTANT, 'a1'),
        Message(USER, 'q2'),
    ]
    assert get_last_usr_msg_idx(messages) == 3
    with pytest.raises(AssertionError):
        get_last_usr_msg_idx([Message(ASSISTANT, 'a')])


def test_rm_default_system():
    # Nothing to remove when there is no leading system message.
    only_user = [Message(USER, 'hi')]
    assert rm_default_system(only_user) == only_user

    # A leading default (empty) system message is removed.
    with_default = [Message(SYSTEM, DEFAULT_SYSTEM_MESSAGE), Message(USER, 'hi')]
    result = rm_default_system(with_default)
    assert len(result) == 1
    assert result[0].role == USER

    # A customized system message is preserved.
    with_custom = [Message(SYSTEM, 'you are a helpful assistant'), Message(USER, 'hi')]
    result = rm_default_system(with_custom)
    assert len(result) == 2
    assert result[0].role == SYSTEM


def test_extract_files_and_images_from_messages():
    messages = [
        Message(USER, [ContentItem(text='hi'), ContentItem(file='/tmp/doc.pdf')]),
        Message(
            ASSISTANT,
            [ContentItem(image='/tmp/img.png'), ContentItem(file='/tmp/other.pdf')]),
        # Duplicate file should not be added twice.
        Message(USER, [ContentItem(file='/tmp/doc.pdf')]),
    ]
    assert extract_files_from_messages(messages, include_images=False) == ['/tmp/doc.pdf', '/tmp/other.pdf']
    assert extract_files_from_messages(messages,
                                       include_images=True) == ['/tmp/doc.pdf', '/tmp/img.png', '/tmp/other.pdf']
    assert extract_images_from_messages(messages) == ['/tmp/img.png']


def test_extract_text_from_message():
    # String content is returned stripped.
    assert extract_text_from_message(Message(USER, '  hi there  '), add_upload_info=False) == 'hi there'
    # Multimodal content: only the text items are concatenated.
    multimodal = Message(USER, [ContentItem(text='part1'), ContentItem(text='part2'), ContentItem(file='/x.pdf')])
    assert extract_text_from_message(multimodal, add_upload_info=False) == 'part1part2'


def test_format_as_text_message():
    multimodal = Message(USER, [ContentItem(text='hello'), ContentItem(file='/x.pdf')])
    msg = format_as_text_message(multimodal, add_upload_info=False)
    assert isinstance(msg.content, str)
    assert msg.content == 'hello'


if __name__ == '__main__':
    test_hash_sha256()
    test_has_chinese_messages()
    test_extract_urls()
    test_extract_markdown_urls()
    test_extract_code()
    test_json_loads()
    test_json_dumps()
    test_merge_generate_cfgs()
    test_get_last_usr_msg_idx()
    test_rm_default_system()
    test_extract_files_and_images_from_messages()
    test_extract_text_from_message()
    test_format_as_text_message()
