from typing import Dict, List, Optional, Union

import json5

from qwen_agent.log import logger
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import get_basename_from_url, print_traceback

from .doc_parser import DocParser, FileTypeNotImplError
from .similarity_search import (RefMaterialInput, RefMaterialInputItem,
                                SimilaritySearch)


def format_records(records: List[Dict]):
    formatted_records = []
    for record in records:
        formatted_records.append(
            RefMaterialInput(url=get_basename_from_url(record['url']),
                             text=[
                                 RefMaterialInputItem(
                                     content=x['page_content'],
                                     token=x['token']) for x in record['raw']
                             ]))
    return formatted_records


@register_tool('retrieval')
class Retrieval(BaseTool):
    description = '从给定文件列表中检索出和问题相关的内容'
    parameters = [{
        'name': 'query',
        'type': 'string',
        'description': '问题，需要从文档中检索和这个问题有关的内容'
    }, {
        'name': 'files',
        'type': 'array',
        'items': {
            'type': 'string'
        },
        'description': '待解析的文件路径列表',
        'required': True
    }]

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.doc_parse = DocParser()
        self.search = SimilaritySearch()

    def call(self,
             params: Union[str, dict],
             ignore_cache: bool = False,
             max_token: int = 4000) -> list:
        """RAG tool.

        Step1: Parse and save files
        Step2: Retrieval related content according to query

        Args:
            params: The files and query.
            ignore_cache: When set to True, overwrite the same documents that have been parsed before.
            max_token: Maximum retrieval length.

        Returns:
            The retrieved file list.
        """

        params = self._verify_json_format_args(params)
        files = params.get('files', [])
        if isinstance(files, str):
            files = json5.loads(files)
        records = []
        for file in files:
            try:
                _record = self.doc_parse.call(params={'url': file},
                                              ignore_cache=ignore_cache)
                records.append(_record)
            except FileTypeNotImplError:
                logger.warning(
                    'Only Parsing the Following File Types: [\'web page\', \'.pdf\', \'.docx\', \'.pptx\'] to knowledge base!'
                )
            except Exception:
                print_traceback()

        query = params.get('query', '')
        if query and records:
            records = format_records(records)
            return self._retrieve_content(query, records, max_token)
        else:
            return records

    def _retrieve_content(self,
                          query: str,
                          records: List[RefMaterialInput],
                          max_token=4000) -> List[Dict]:
        single_max_token = int(max_token / len(records))
        _ref_list = []
        for record in records:
            # Retrieval for query
            now_ref_list = self.search.call(params={'query': query},
                                            doc=record,
                                            max_token=single_max_token)
            _ref_list.append(now_ref_list)
        return _ref_list
