from .amap_weather import AmapWeather
from .base import TOOL_REGISTRY, BaseTool
from .code_interpreter import CodeInterpreter
from .doc_parser import DocParser
from .image_gen import ImageGen
from .retrieval import Retrieval
from .similarity_search import SimilaritySearch
from .storage import Storage
from .web_extractor import WebExtractor


def call_tool(plugin_name: str, plugin_args: str) -> str:
    if plugin_name in TOOL_REGISTRY:
        return TOOL_REGISTRY[plugin_name].call(plugin_args)
    else:
        raise NotImplementedError


__all__ = [
    'BaseTool', 'CodeInterpreter', 'ImageGen', 'AmapWeather', 'TOOL_REGISTRY',
    'DocParser', 'SimilaritySearch', 'Storage', 'Retrieval', 'WebExtractor'
]
