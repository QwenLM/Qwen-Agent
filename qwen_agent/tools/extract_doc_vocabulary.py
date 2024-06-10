import json
import os
from typing import Dict, Optional, Union

import json5

from qwen_agent.settings import DEFAULT_WORKSPACE
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.tools.search_tools.keyword_search import WORDS_TO_IGNORE, string_tokenizer
from qwen_agent.tools.simple_doc_parser import SimpleDocParser
from qwen_agent.tools.storage import KeyNotExistsError, Storage


@register_tool('extract_doc_vocabulary')
class ExtractDocVocabulary(BaseTool):
    description = '提取文档的词表。'
    parameters = [{
        'name': 'files',
        'type': 'array',
        'items': {
            'type': 'string'
        },
        'description': '文件路径列表，支持本地文件路径或可下载的http(s)链接。',
        'required': True
    }]

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.simple_doc_parse = SimpleDocParser()

        self.data_root = self.cfg.get('path', os.path.join(DEFAULT_WORKSPACE, 'tools', self.name))
        self.db = Storage({'storage_root_path': self.data_root})

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        files = params.get('files', [])
        document_id = str(files)

        if isinstance(files, str):
            files = json5.loads(files)
        docs = []
        for file in files:
            _doc = self.simple_doc_parse.call(params={'url': file}, **kwargs)
            docs.append(_doc)

        try:
            all_voc = self.db.call({'operate': 'get', 'key': document_id})
        except KeyNotExistsError:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
            except ModuleNotFoundError:
                raise ModuleNotFoundError('Please install sklearn by: `pip install scikit-learn`')

            vectorizer = TfidfVectorizer(tokenizer=string_tokenizer, stop_words=WORDS_TO_IGNORE)
            tfidf_matrix = vectorizer.fit_transform(docs)
            sorted_items = sorted(zip(vectorizer.get_feature_names_out(),
                                      tfidf_matrix.toarray().flatten()),
                                  key=lambda x: x[1],
                                  reverse=True)
            all_voc = ', '.join([term for term, score in sorted_items])
            if document_id:
                self.db.call({'operate': 'put', 'key': document_id, 'value': json.dumps(all_voc, ensure_ascii=False)})

        return all_voc
