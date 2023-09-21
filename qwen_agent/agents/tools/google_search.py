import os

import json5

from langchain import SerpAPIWrapper


def google_search(plugin_args):
    # 使用 SerpAPI 需要在这里填入您的 SERPAPI_API_KEY！
    os.environ['SERPAPI_API_KEY'] = os.getenv('SERPAPI_API_KEY', default='')

    return SerpAPIWrapper().run(json5.loads(plugin_args)['search_query'])
