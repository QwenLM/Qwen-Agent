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

import re

from qwen_agent.utils.utils import has_chinese_chars


def rm_newlines(text):
    if text.endswith('-\n'):
        text = text[:-2]
        return text.strip()
    rep_c = ' '
    if has_chinese_chars(text):
        rep_c = ''
    text = re.sub(r'(?<=[^\.。:：\d])\n', rep_c, text)
    return text.strip()


def rm_cid(text):
    text = re.sub(r'\(cid:\d+\)', '', text)
    return text


def rm_hexadecimal(text):
    text = re.sub(r'[0-9A-Fa-f]{21,}', '', text)
    return text


def rm_continuous_placeholders(text):
    text = re.sub(r'[.\- —。_*]{7,}', '\t', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text
