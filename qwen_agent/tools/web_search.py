import os
from typing import Any, List, Union

import requests

from qwen_agent.tools.base import BaseTool, register_tool

SERPER_API_KEY = os.getenv('SERPER_API_KEY', '')
SERPER_URL = os.getenv('SERPER_URL', 'https://google.serper.dev/search')


@register_tool('web_search', allow_overwrite=True)
class WebSearch(BaseTool):
    name = 'web_search'
    description = 'Search for information from the internet.'
    parameters = {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
            }
        },
        'required': ['query'],
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        query = params['query']

        search_results = self.search(query)
        formatted_results = self._format_results(search_results)
        return formatted_results

    @staticmethod
    def search(query: str) -> List[Any]:
        if not SERPER_API_KEY:
            raise ValueError(
                'SERPER_API_KEY is None! Please Apply for an apikey from https://serper.dev and set it as an environment variable by `export SERPER_API_KEY=xxxxxx`'
            )
        headers = {'Content-Type': 'application/json', 'X-API-KEY': SERPER_API_KEY}
        payload = {'q': query}
        response = requests.post(SERPER_URL, json=payload, headers=headers)
        response.raise_for_status()

        return response.json()['organic']

    @staticmethod
    def _format_results(search_results: List[Any]) -> str:
        content = '```\n{}\n```'.format('\n\n'.join([
            f"[{i}]\"{doc['title']}\n{doc.get('snippet', '')}\"{doc.get('date', '')}"
            for i, doc in enumerate(search_results, 1)
        ]))
        return content
