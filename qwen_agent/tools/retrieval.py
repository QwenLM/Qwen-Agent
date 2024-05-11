from typing import Dict, Optional, Union

import json5

from qwen_agent.settings import DEFAULT_MAX_REF_TOKEN, DEFAULT_PARSER_PAGE_SIZE, DEFAULT_RAG_SEARCHERS
from qwen_agent.tools.base import TOOL_REGISTRY, BaseTool, register_tool
from qwen_agent.tools.doc_parser import DocParser, Record
from qwen_agent.tools.simple_doc_parser import PARSER_SUPPORTED_FILE_TYPES


@register_tool('retrieval')
class Retrieval(BaseTool):
    description = f'从给定文件列表中检索出和问题相关的内容，支持文件类型包括：{"/".join(PARSER_SUPPORTED_FILE_TYPES)}'
    parameters = [{
        'name': 'query',
        'type': 'string',
        'description': '在这里列出关键词，用逗号分隔，目的是方便在文档中匹配到相关的内容，由于文档可能多语言，关键词最好中英文都有。',
        'required': True
    }, {
        'name': 'files',
        'type': 'array',
        'items': {
            'type': 'string'
        },
        'description': '待解析的文件路径列表，支持本地文件路径或可下载的http(s)链接。',
        'required': True
    }]

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.doc_parse = DocParser()
        self.searchers = self.cfg.get('rag_searchers', DEFAULT_RAG_SEARCHERS)
        if len(self.searchers) == 1:
            self.search = TOOL_REGISTRY[self.searchers[0]]()
        else:
            from qwen_agent.tools.search_tools.hybrid_search import HybridSearch
            self.search = HybridSearch({'rag_searchers': self.searchers})

    def call(self,
             params: Union[str, dict],
             ignore_cache: bool = False,
             max_ref_token: int = DEFAULT_MAX_REF_TOKEN,
             parser_page_size: int = DEFAULT_PARSER_PAGE_SIZE,
             **kwargs) -> list:
        """RAG tool.

        Step1: Parse and save files
        Step2: Retrieval related content according to query

        Args:
            params: The files and query.
            ignore_cache: When set to True, overwrite the same documents that have been parsed before.
            max_ref_token: Maximum retrieval length.
            parser_page_size: The size of one page for doc parser.

        Returns:
            The parsed file list or retrieved file list.
        """

        params = self._verify_json_format_args(params)
        files = params.get('files', [])
        if isinstance(files, str):
            files = json5.loads(files)
        records = []
        for file in files:
            _record = self.doc_parse.call(params={'url': file},
                                          ignore_cache=ignore_cache,
                                          parser_page_size=parser_page_size,
                                          max_ref_token=max_ref_token)
            records.append(_record)

        query = params.get('query', '')
        if records:
            return self.search.call(params={'query': query},
                                    docs=[Record(**rec) for rec in records],
                                    max_ref_token=max_ref_token)
        else:
            return []
