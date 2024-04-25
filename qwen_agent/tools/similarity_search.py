from typing import List, Union

import jieba
import json5
from pydantic import BaseModel

from qwen_agent.log import logger
from qwen_agent.settings import DEFAULT_MAX_REF_TOKEN
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.tools.doc_parser import DocParser, Record
from qwen_agent.utils.tokenization_qwen import count_tokens, tokenizer
from qwen_agent.utils.utils import has_chinese_chars


class RefMaterialOutput(BaseModel):
    """The knowledge data format output from the retrieval"""
    url: str
    text: list

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'text': self.text,
        }


def format_input_doc(doc: List[str], url: str = '') -> Record:
    new_doc = []
    parser = DocParser()
    for i, x in enumerate(doc):
        page = {'page_num': i, 'content': [{'text': x, 'token': count_tokens(x)}]}
        new_doc.append(page)
    content = parser.split_doc_to_chunk(new_doc, path=url)
    return Record(url=url, raw=content, title='')


@register_tool('similarity_search')
class SimilaritySearch(BaseTool):
    description = '从给定文档中检索和问题相关的部分'
    parameters = [{'name': 'query', 'type': 'string', 'description': '问题，需要从文档中检索和这个问题有关的内容', 'required': True}]

    def call(
        self,
        params: Union[str, dict],
        docs: List[Union[Record, str, List[str]]] = None,
        max_token: int = DEFAULT_MAX_REF_TOKEN,
    ) -> list:
        params = self._verify_json_format_args(params)

        query = params['query']
        if not docs:
            return []
        new_docs = []
        all_tokens = 0
        for i, doc in enumerate(docs):
            if isinstance(doc, str):
                doc = [doc]  # Doc with one page
            if isinstance(doc, list):
                doc = format_input_doc(doc, f'doc_{str(i)}')

            if isinstance(doc, Record):
                new_docs.append(doc)
                all_tokens += sum([page.token for page in doc.raw])
            else:
                raise TypeError
        logger.info(f'all tokens: {all_tokens}')
        if all_tokens <= max_token:
            # Todo: Whether to use full window
            logger.info('use full ref')
            return [
                RefMaterialOutput(url=doc.url, text=[page.content for page in doc.raw]).to_dict() for doc in new_docs
            ]

        wordlist = parse_keyword(query)
        logger.info('wordlist: ' + ','.join(wordlist))
        if not wordlist:
            # Todo: This represents the queries that do not use retrieval: summarize, etc.
            return self.get_top(new_docs, max_token)

        # Mix all chunks
        docs_map = {}  # {'text id': ['doc id', 'chunk id']}
        text_list = []  # ['text 1', 'text 2', ...]
        docs_retrieved = []  # [{'url': 'doc id', 'text': []}]
        for i, doc in enumerate(new_docs):
            docs_retrieved.append(RefMaterialOutput(url=doc.url, text=[''] * len(doc.raw)))
            for j, page in enumerate(doc.raw):
                docs_map[len(text_list)] = [i, j]
                text_list.append(page.content)
        assert len(docs_map) == len(text_list)

        # Using bm25 retrieval
        from rank_bm25 import BM25Okapi
        bm25 = BM25Okapi([split_text_into_keywords(x) for x in text_list])
        doc_scores = bm25.get_scores(wordlist)
        sims = [[i, sim] for i, sim in enumerate(doc_scores)]
        sims.sort(key=lambda item: item[1], reverse=True)
        assert len(sims) > 0
        max_sims = sims[0][1]
        available_token = max_token
        if max_sims != 0:
            if len(new_docs) == 1:
                # This is a trick for improving performance for one doc
                manual = 2
                for doc_id, doc in enumerate(new_docs):
                    for chunk_id in range(min(manual, len(doc.raw))):
                        page = doc.raw[chunk_id]
                        if available_token >= page.token * manual * 2:  # Ensure that the first two pages do not fill up the window
                            docs_retrieved[doc_id].text[chunk_id] = page.content
                            available_token -= page.token
                        else:
                            break
            for (index, sim) in sims:
                # Retrieval by BM25
                if available_token <= 0:
                    break
                doc_id = docs_map[index][0]
                chunk_id = docs_map[index][1]
                page = new_docs[doc_id].raw[chunk_id]
                if docs_retrieved[doc_id].text[chunk_id]:
                    # Has retrieved
                    continue
                if available_token < page.token:
                    docs_retrieved[doc_id].text[chunk_id] = tokenizer.truncate(page.content, max_token=available_token)
                    break
                docs_retrieved[doc_id].text[chunk_id] = page.content
                available_token -= page.token

            res = []
            for x in docs_retrieved:
                x.text = [trk for trk in x.text if trk]
                if x.text:
                    res.append(x.to_dict())
            return res
        else:
            return self.get_top(new_docs, max_token)

    @staticmethod
    def get_top(docs: List[Record], max_token: int = DEFAULT_MAX_REF_TOKEN) -> list:
        single_max_token = int(max_token / len(docs))
        _ref_list = []
        for doc in docs:
            available_token = single_max_token
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


def string_tokenizer(text: str) -> List[str]:
    text = text.lower()
    if has_chinese_chars(text):
        _wordlist = list(jieba.lcut(text.strip()))
    else:
        _wordlist = text.strip().split()
    return _wordlist


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
