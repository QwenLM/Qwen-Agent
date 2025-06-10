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
import string
from typing import List, Tuple

import json5

from qwen_agent.log import logger
from qwen_agent.settings import DEFAULT_MAX_REF_TOKEN
from qwen_agent.tools.base import register_tool
from qwen_agent.tools.doc_parser import Record
from qwen_agent.tools.search_tools.base_search import BaseSearch
from qwen_agent.utils.utils import has_chinese_chars


@register_tool('keyword_search')
class KeywordSearch(BaseSearch):

    def search(self, query: str, docs: List[Record], max_ref_token: int = DEFAULT_MAX_REF_TOKEN) -> list:
        chunk_and_score = self.sort_by_scores(query=query, docs=docs)
        if not chunk_and_score:
            return self._get_the_front_part(docs, max_ref_token)

        max_sims = chunk_and_score[0][-1]

        if max_sims != 0:
            return super().get_topk(chunk_and_score=chunk_and_score, docs=docs, max_ref_token=max_ref_token)
        else:
            return self._get_the_front_part(docs, max_ref_token)

    def sort_by_scores(self, query: str, docs: List[Record], **kwargs) -> List[Tuple[str, int, float]]:
        wordlist = parse_keyword(query)
        logger.debug('wordlist: ' + ','.join(wordlist))
        if not wordlist:
            # This represents the queries that do not use retrieval: summarize, etc.
            return []

        # Plain all chunks from all docs
        all_chunks = []
        for doc in docs:
            all_chunks.extend(doc.raw)

        # Using bm25 retrieval
        from rank_bm25 import BM25Okapi
        bm25 = BM25Okapi([split_text_into_keywords(x.content) for x in all_chunks])
        doc_scores = bm25.get_scores(wordlist)
        chunk_and_score = [
            (chk.metadata['source'], chk.metadata['chunk_id'], score) for chk, score in zip(all_chunks, doc_scores)
        ]
        chunk_and_score.sort(key=lambda item: item[2], reverse=True)
        assert len(chunk_and_score) > 0

        return chunk_and_score


WORDS_TO_IGNORE = [
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd", 'your',
    'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers', 'herself', 'it',
    "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this',
    'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until',
    'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before',
    'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
    'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few',
    'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y',
    'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn',
    "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't",
    'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn',
    "wouldn't", '', '\\t', '\\n', '\\\\', '\n', '\t', '\\', ' ', ',', '，', ';', '；', '/', '.', '。', '-', '_', '——', '的',
    '吗', '是', '了', '啊', '呢', '怎么', '如何', '什么', '(', ')', '（', '）', '【', '】', '[', ']', '{', '}', '？', '?', '！', '!',
    '“', '”', '‘', '’', "'", '"', ':', '：', '讲了', '描述', '讲', '总结', 'summarize', '总结下', '总结一下', '文档', '文章', 'article',
    'paper', '文稿', '稿子', '论文', 'PDF', 'pdf', '这个', '这篇', '这', '我', '帮我', '那个', '下', '翻译', '说说', '讲讲', '介绍', 'summary'
]

ENGLISH_PUNCTUATIONS = string.punctuation.replace('%', '').replace('.', '').replace(
    '@', '')  # English punctuations to remove. We're separately handling %, ., and @
CHINESE_PUNCTUATIONS = '。？！，、；：“”‘’（）《》【】……—『』「」_'
PUNCTUATIONS = ENGLISH_PUNCTUATIONS + CHINESE_PUNCTUATIONS


def clean_en_token(token: str) -> str:

    punctuations_to_strip = PUNCTUATIONS

    # Detect if the token is a special case like U.S.A., E-mail, percentage, etc.
    # and skip further processing if that is the case.
    special_cases_pattern = re.compile(r'^(?:[A-Za-z]\.)+|\w+[@]\w+\.\w+|\d+%$|^(?:[\u4e00-\u9fff]+)$')
    if special_cases_pattern.match(token):
        return token

    # Strip unwanted punctuations from front and end
    token = token.strip(punctuations_to_strip)

    return token


def tokenize_and_filter(input_text: str) -> str:
    patterns = r"""(?x)                    # Enable verbose mode, allowing regex to be on multiple lines and ignore whitespace
                (?:[A-Za-z]\.)+          # Match abbreviations, e.g., U.S.A.
                |\d+(?:\.\d+)?%?         # Match numbers, including percentages
                |\w+(?:[-']\w+)*         # Match words, allowing for hyphens and apostrophes
                |(?:[\w\-\']@)+\w+       # Match email addresses
                """

    tokens = re.findall(patterns, input_text)

    stop_words = WORDS_TO_IGNORE

    filtered_tokens = []
    for token in tokens:
        token_lower = clean_en_token(token).lower()
        if token_lower not in stop_words and not all(char in PUNCTUATIONS for char in token_lower):
            filtered_tokens.append(token_lower)

    return filtered_tokens


def string_tokenizer(text: str) -> List[str]:
    text = text.lower().strip()
    if has_chinese_chars(text):
        import jieba
        _wordlist_tmp = list(jieba.lcut(text))
        _wordlist = []
        for word in _wordlist_tmp:
            if not all(char in PUNCTUATIONS for char in word):
                _wordlist.append(word)
    else:
        try:
            _wordlist = tokenize_and_filter(text)
        except Exception:
            logger.warning('Tokenize words by spaces.')
            _wordlist = text.split()
    _wordlist_res = []
    for word in _wordlist:
        if word in WORDS_TO_IGNORE:
            continue
        else:
            _wordlist_res.append(word)

    import snowballstemmer
    stemmer = snowballstemmer.stemmer('english')
    return stemmer.stemWords(_wordlist_res)


def split_text_into_keywords(text: str) -> List[str]:
    _wordlist = string_tokenizer(text)
    wordlist = []
    for x in _wordlist:
        if x in WORDS_TO_IGNORE:
            continue
        wordlist.append(x)
    return wordlist


def parse_keyword(text):
    try:
        res = json5.loads(text)
    except Exception:
        return split_text_into_keywords(text)

    import snowballstemmer
    stemmer = snowballstemmer.stemmer('english')

    # json format
    _wordlist = []
    try:
        if 'keywords_zh' in res and isinstance(res['keywords_zh'], list):
            _wordlist.extend([kw.lower() for kw in res['keywords_zh']])
        if 'keywords_en' in res and isinstance(res['keywords_en'], list):
            _wordlist.extend([kw.lower() for kw in res['keywords_en']])
        _wordlist = stemmer.stemWords(_wordlist)
        wordlist = []
        for x in _wordlist:
            if x in WORDS_TO_IGNORE:
                continue
            wordlist.append(x)
        split_wordlist = split_text_into_keywords(res['text'])
        wordlist += split_wordlist
        return wordlist
    except Exception:
        # TODO: This catch is too broad.
        return split_text_into_keywords(text)
