from typing import List, Tuple

import jieba
import json5
import snowballstemmer

from qwen_agent.log import logger
from qwen_agent.settings import DEFAULT_MAX_REF_TOKEN
from qwen_agent.tools.base import register_tool
from qwen_agent.tools.doc_parser import Record
from qwen_agent.tools.search_tools.base_search import BaseSearch, RefMaterialOutput
from qwen_agent.utils.tokenization_qwen import tokenizer
from qwen_agent.utils.utils import has_chinese_chars


@register_tool('keyword_search')
class KeywordSearch(BaseSearch):

    def search(self, query: str, docs: List[Record], max_ref_token: int = DEFAULT_MAX_REF_TOKEN) -> list:
        chunk_and_score = self.sort_by_scores(query=query, docs=docs)
        if not chunk_and_score:
            return self._get_the_front_part(docs, max_ref_token)

        max_sims = chunk_and_score[0][1]
        if max_sims != 0:
            return super().get_topk(chunk_and_score=chunk_and_score, docs=docs, max_ref_token=max_ref_token)
        else:
            return self._get_the_front_part(docs, max_ref_token)

    def sort_by_scores(self, query: str, docs: List[Record], **kwargs) -> List[Tuple[str, int, float]]:
        wordlist = parse_keyword(query)
        logger.info('wordlist: ' + ','.join(wordlist))
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

    @staticmethod
    def _get_the_front_part(docs: List[Record], max_ref_token: int = DEFAULT_MAX_REF_TOKEN) -> list:
        single_max_ref_token = int(max_ref_token / len(docs))
        _ref_list = []
        for doc in docs:
            available_token = single_max_ref_token
            text = []
            for page in doc.raw:
                if available_token <= 0:
                    break
                if page.token <= available_token:
                    text.append(page.content)
                    available_token -= page.token
                else:
                    text.append(tokenizer.truncate(page.content, max_token=available_token))
                    break
            logger.info(f'[Get top] Remaining slots: {available_token}')
            now_ref_list = RefMaterialOutput(url=doc.url, text=text).to_dict()
            _ref_list.append(now_ref_list)
        return _ref_list


WORDS_TO_IGNORE = [
    '', '\\t', '\\n', '\\\\', '\\', '', '\n', '\t', '\\', ' ', ',', '，', ';', '；', '/', '.', '。', '-', 'is', 'are',
    'am', 'what', 'how', '的', '吗', '是', '了', '啊', '呢', '怎么', '如何', '什么', '(', ')', '（', '）', '【', '】', '[', ']', '{',
    '}', '？', '?', '！', '!', '“', '”', '‘', '’', "'", "'", '"', '"', ':', '：', '讲了', '描述', '讲', '总结', 'summarize',
    '总结下', '总结一下', '文档', '文章', 'article', 'paper', '文稿', '稿子', '论文', 'PDF', 'pdf', '这个', '这篇', '这', '我', '帮我', '那个',
    '下', '翻译', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll",
    "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers',
    'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who',
    'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because',
    'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
    'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few',
    'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y',
    'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn',
    "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't",
    'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn',
    "wouldn't", '说说', '讲讲', '介绍', 'summary'
]

STEMMER = snowballstemmer.stemmer('english')


def string_tokenizer(text: str) -> List[str]:
    text = text.lower()
    if has_chinese_chars(text):
        _wordlist = list(jieba.lcut(text.strip()))
    else:
        _wordlist = text.strip().split()
    return STEMMER.stemWords(_wordlist)


def split_text_into_keywords(text: str) -> List[str]:
    _wordlist = string_tokenizer(text)
    wordlist = []
    for x in _wordlist:
        if x in WORDS_TO_IGNORE or x in wordlist:
            continue
        wordlist.append(x)
    return wordlist


def parse_keyword(text):
    try:
        res = json5.loads(text)
    except Exception:
        return split_text_into_keywords(text)

    # json format
    _wordlist = []
    try:
        if 'keywords_zh' in res and isinstance(res['keywords_zh'], list):
            _wordlist.extend([kw.lower() for kw in res['keywords_zh']])
        if 'keywords_en' in res and isinstance(res['keywords_en'], list):
            _wordlist.extend([kw.lower() for kw in res['keywords_en']])
        _wordlist = STEMMER.stemWords(_wordlist)
        wordlist = []
        for x in _wordlist:
            if x in WORDS_TO_IGNORE:
                continue
            wordlist.append(x)
        split_wordlist = split_text_into_keywords(res['text'])
        for x in split_wordlist:
            if x in wordlist:
                continue
            wordlist.append(x)
        return wordlist
    except Exception:
        return split_text_into_keywords(text)
