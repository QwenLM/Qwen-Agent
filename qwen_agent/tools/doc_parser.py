import json
import os
import re
import time
from typing import Dict, List, Optional, Union

from pydantic import BaseModel

from qwen_agent.log import logger
from qwen_agent.settings import DEFAULT_MAX_REF_TOKEN, DEFAULT_PARSER_PAGE_SIZE, DEFAULT_WORKSPACE
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.tools.simple_doc_parser import PARAGRAPH_SPLIT_SYMBOL, SimpleDocParser, get_plain_doc
from qwen_agent.tools.storage import KeyNotExistsError, Storage
from qwen_agent.utils.tokenization_qwen import count_tokens, tokenizer
from qwen_agent.utils.utils import get_basename_from_url, hash_sha256


class Chunk(BaseModel):
    content: str
    metadata: dict
    token: int

    def __init__(self, content: str, metadata: dict, token: int):
        super().__init__(content=content, metadata=metadata, token=token)

    def to_dict(self) -> dict:
        return {'content': self.content, 'metadata': self.metadata, 'token': self.token}


class Record(BaseModel):
    url: str
    raw: List[Chunk]
    title: str

    def __init__(self, url: str, raw: List[Chunk], title: str):
        super().__init__(url=url, raw=raw, title=title)

    def to_dict(self) -> dict:
        return {'url': self.url, 'raw': [x.to_dict() for x in self.raw], 'title': self.title}


@register_tool('doc_parser')
class DocParser(BaseTool):
    description = '对一个文件进行内容提取和分块、返回分块后的文件内容'
    parameters = [{
        'name': 'url',
        'type': 'string',
        'description': '待解析的文件的路径，可以是一个本地路径或可下载的http(s)链接',
        'required': True
    }]

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.max_ref_token: int = self.cfg.get('max_ref_token', DEFAULT_MAX_REF_TOKEN)
        self.parser_page_size: int = self.cfg.get('parser_page_size', DEFAULT_PARSER_PAGE_SIZE)

        self.data_root = self.cfg.get('path', os.path.join(DEFAULT_WORKSPACE, 'tools', self.name))
        self.db = Storage({'storage_root_path': self.data_root})

        self.doc_extractor = SimpleDocParser({'structured_doc': True})

    def call(self, params: Union[str, dict], **kwargs) -> dict:
        """Extracting and blocking

        Returns:
            Parse doc as the following chunks:
              {
                'url': 'This is the url of this file',
                'title': 'This is the extracted title of this file',
                'raw': [
                        {
                            'content': 'This is one chunk',
                            'token': 'The token number',
                            'metadata': {}  # some information of this chunk
                        },
                        ...,
                      ]
             }
        """

        params = self._verify_json_format_args(params)
        # Compatible with the parameter passing of the qwen-agent version <= 0.0.3
        max_ref_token = kwargs.get('max_ref_token', self.max_ref_token)
        parser_page_size = kwargs.get('parser_page_size', self.parser_page_size)

        url = params['url']

        cached_name_chunking = f'{hash_sha256(url)}_{str(parser_page_size)}'
        try:
            # Directly load the chunked doc
            record = self.db.get(cached_name_chunking)
            record = json.loads(record)
            logger.info(f'Read chunked {url} from cache.')
            return record
        except KeyNotExistsError:
            doc = self.doc_extractor.call({'url': url})

        total_token = 0
        for page in doc:
            for para in page['content']:
                total_token += para['token']

        if doc and 'title' in doc[0]:
            title = doc[0]['title']
        else:
            title = get_basename_from_url(url)

        logger.info(f'Start chunking {url} ({title})...')
        time1 = time.time()
        if total_token <= max_ref_token:
            # The whole doc is one chunk
            content = [
                Chunk(content=get_plain_doc(doc),
                      metadata={
                          'source': url,
                          'title': title,
                          'chunk_id': 0
                      },
                      token=total_token)
            ]
            cached_name_chunking = f'{hash_sha256(url)}_without_chunking'
        else:
            content = self.split_doc_to_chunk(doc, url, title=title, parser_page_size=parser_page_size)

        time2 = time.time()
        logger.info(f'Finished chunking {url} ({title}). Time spent: {time2 - time1} seconds.')

        # save the document data
        new_record = Record(url=url, raw=content, title=title).to_dict()
        new_record_str = json.dumps(new_record, ensure_ascii=False)
        self.db.put(cached_name_chunking, new_record_str)
        return new_record

    def split_doc_to_chunk(self,
                           doc: List[dict],
                           path: str,
                           title: str = '',
                           parser_page_size: int = DEFAULT_PARSER_PAGE_SIZE) -> List[Chunk]:
        res = []
        chunk = []
        available_token = parser_page_size
        has_para = False
        for page in doc:
            page_num = page['page_num']
            if not chunk or f'[page: {str(page_num)}]' != chunk[0]:
                chunk.append(f'[page: {str(page_num)}]')
            idx = 0
            len_para = len(page['content'])
            while idx < len_para:
                if not chunk:
                    chunk.append(f'[page: {str(page_num)}]')
                para = page['content'][idx]
                txt = para.get('text', para.get('table'))
                token = para['token']
                if token <= available_token:
                    available_token -= token
                    chunk.append([txt, page_num])
                    has_para = True
                    idx += 1
                else:
                    if has_para:
                        # Record one chunk
                        if isinstance(chunk[-1], str) and re.fullmatch(r'^\[page: \d+\]$', chunk[-1]) is not None:
                            chunk.pop()  # Redundant page information
                        res.append(
                            Chunk(content=PARAGRAPH_SPLIT_SYMBOL.join(
                                [x if isinstance(x, str) else x[0] for x in chunk]),
                                  metadata={
                                      'source': path,
                                      'title': title,
                                      'chunk_id': len(res)
                                  },
                                  token=parser_page_size - available_token))

                        # Define new chunk
                        overlap_txt = self._get_last_part(chunk)
                        if overlap_txt.strip():
                            chunk = [f'[page: {str(chunk[-1][1])}]', overlap_txt]
                            has_para = False
                            available_token = parser_page_size - count_tokens(overlap_txt)
                        else:
                            chunk = []
                            has_para = False
                            available_token = parser_page_size
                    else:
                        # There are excessively long paragraphs present
                        # Split paragraph to sentences
                        _sentences = re.split(r'\. |。', txt)
                        sentences = []
                        for s in _sentences:
                            token = count_tokens(s)
                            if not s.strip() or token == 0:
                                continue
                            if token <= available_token:
                                sentences.append([s, token])
                            else:
                                # Limit the length of a sentence to chunk size
                                token_list = tokenizer.tokenize(s)
                                for si in range(0, len(token_list), available_token):
                                    ss = tokenizer.convert_tokens_to_string(
                                        token_list[si:min(len(token_list), si + available_token)])
                                    sentences.append([ss, min(available_token, len(token_list) - si)])
                        sent_index = 0
                        while sent_index < len(sentences):
                            s = sentences[sent_index][0]
                            token = sentences[sent_index][1]
                            if not chunk:
                                chunk.append(f'[page: {str(page_num)}]')

                            if token <= available_token or (not has_para):
                                # Be sure to add at least one sentence
                                # (not has_para) is a patch of the previous sentence splitting
                                available_token -= token
                                chunk.append([s, page_num])
                                has_para = True
                                sent_index += 1
                            else:
                                assert has_para
                                if isinstance(chunk[-1], str) and re.fullmatch(r'^\[page: \d+\]$',
                                                                               chunk[-1]) is not None:
                                    chunk.pop()  # Redundant page information
                                res.append(
                                    Chunk(content=PARAGRAPH_SPLIT_SYMBOL.join(
                                        [x if isinstance(x, str) else x[0] for x in chunk]),
                                          metadata={
                                              'source': path,
                                              'title': title,
                                              'chunk_id': len(res)
                                          },
                                          token=parser_page_size - available_token))

                                overlap_txt = self._get_last_part(chunk)
                                if overlap_txt.strip():
                                    chunk = [f'[page: {str(chunk[-1][1])}]', overlap_txt]
                                    has_para = False
                                    available_token = parser_page_size - count_tokens(overlap_txt)
                                else:
                                    chunk = []
                                    has_para = False
                                    available_token = parser_page_size
                        # Has split this paragraph by sentence
                        idx += 1
        if has_para:
            if isinstance(chunk[-1], str) and re.fullmatch(r'^\[page: \d+\]$', chunk[-1]) is not None:
                chunk.pop()  # Redundant page information
            res.append(
                Chunk(content=PARAGRAPH_SPLIT_SYMBOL.join([x if isinstance(x, str) else x[0] for x in chunk]),
                      metadata={
                          'source': path,
                          'title': title,
                          'chunk_id': len(res)
                      },
                      token=parser_page_size - available_token))

        return res

    def _get_last_part(self, chunk: list) -> str:
        overlap = ''
        need_page = chunk[-1][1]  # Only need this page to prepend
        available_len = 150
        for i in range(len(chunk) - 1, -1, -1):
            if not (isinstance(chunk[i], list) and len(chunk[i]) == 2):
                continue
            if chunk[i][1] != need_page:
                return overlap
            para = chunk[i][0]
            if len(para) <= available_len:
                if overlap:
                    overlap = f'{para}{PARAGRAPH_SPLIT_SYMBOL}{overlap}'
                else:
                    overlap = f'{para}'
                available_len -= len(para)
                continue
            sentence_split_symbol = '. '
            if '。' in para:
                sentence_split_symbol = '。'
            sentences = re.split(r'\. |。', para)
            sentences = [sentence.strip() for sentence in sentences if sentence]
            for j in range(len(sentences) - 1, -1, -1):
                sent = sentences[j]
                if not sent.strip():
                    continue
                if len(sent) <= available_len:
                    if overlap:
                        overlap = f'{sent}{sentence_split_symbol}{overlap}'
                    else:
                        overlap = f'{sent}'
                    available_len -= len(sent)
                else:
                    return overlap
        return overlap
