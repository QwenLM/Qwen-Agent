from typing import Union

from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.tools.simple_doc_parser import SimpleDocParser


@register_tool('web_extractor')
class WebExtractor(BaseTool):
    description = '根据网页URL，获取网页内容的工具'
    parameters = [{'name': 'url', 'type': 'string', 'description': '网页URL', 'required': True}]

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        url = params['url']
        parsed_web = SimpleDocParser().call({'url': url})
        return parsed_web
