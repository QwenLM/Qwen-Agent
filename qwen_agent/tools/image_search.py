# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import random
import time
from typing import Dict, List, Optional, OrderedDict, Tuple, Union
import requests

from pydantic import BaseModel, Field

import socket
import requests.packages.urllib3.util.connection as connection
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.log import logger
from qwen_agent.llm.schema import Message, ContentItem
from qwen_agent.utils.utils import extract_images_from_messages


SERPAPI_IMAGE_SEARCH_KEY = os.getenv('SERPAPI_IMAGE_SEARCH_KEY', '')
QWEN_IMAGE_SEARCH_MAX_RETRY_TIMES = int(os.getenv('QWEN_IMAGE_SEARCH_MAX_RETRY_TIMES', '3'))
SERPAPI_URL = 'https://serpapi.com/search.json'

_orig_getaddrinfo = socket.getaddrinfo

def _new_getaddrinfo(*args, **kwargs):
    responses = _orig_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]

socket.getaddrinfo = _new_getaddrinfo

class ImageResult(BaseModel):
    """
    Represents an image search result with URL, title, and metadata.
    """
    id: str = Field(..., description='Unique identifier for the image')
    title: str = Field(..., description='Title or caption of the image')
    imgurl: str = Field(..., description='Direct URL to the image')
    url: str = Field(..., description='Source page URL where the image was found')
    width: str = Field(..., description='Image width in pixels')
    height: str = Field(..., description='Image height in pixels')
    content: str = Field(default='', description='Additional content or description')

    def __str__(self):
        result = {}
        if self.id:
            result['id'] = self.id
        if self.title:
            result['title'] = self.title
        if self.imgurl:
            result['imgurl'] = self.imgurl
        if self.content:
            result['description'] = self.content

        return json.dumps(result, ensure_ascii=False)

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)


def serper_search(image_url: str, check_accessibility: bool = True, max_retry: int = QWEN_IMAGE_SEARCH_MAX_RETRY_TIMES) -> dict:
    """
    Image Search with SerpApi
    """
    if not SERPAPI_IMAGE_SEARCH_KEY:
        raise ValueError(
            'SERPAPI_IMAGE_SEARCH_KEY is None! Please Apply for an apikey from https://serper.dev and set it as an environment variable by `export SERPAPI_IMAGE_SEARCH_KEY=xxxxxx`'
        )

    payload = {
        'engine': 'google_reverse_image',  
        'image_url': image_url,   
        'api_key': SERPAPI_IMAGE_SEARCH_KEY,
        'hl': 'zh-CN', 
        'gl': 'cn',  
    }

    for _ in range(max_retry):
        success = False
        start_time = time.perf_counter()
        response = None
        try:
            response = requests.get(SERPAPI_URL, params=payload)
            response.raise_for_status() 
            json_response = response.json()
            items_data = json_response.get('image_results', []) + json_response.get('inline_images', [])
            results: Dict[str, ImageResult] = OrderedDict()
            for item_data in items_data:
                try:
                    image_direct_url = item_data.get('original', item_data.get('thumbnail')) 
                    source_page_url = item_data.get('link', '')
                    if not image_direct_url:
                        continue
                    image = ImageResult(id=str(item_data.get('position', '')),
                                        title=item_data.get('title', ''),
                                        imgurl=image_direct_url,
                                        url=source_page_url,
                                        width=item_data.get('width', ''),
                                        height=item_data.get('height', ''),
                                        content=item_data.get('snippet', ''))
                    if image.imgurl in results and len(results[image.imgurl].title) > len(image.title):
                        logger.debug(f"Duplicate image found: {image.imgurl}, skipping")
                    else:
                        if check_accessibility:
                            _, is_accessible = check_image_url_accessibility(image.imgurl)
                            if is_accessible:
                                results[image.imgurl] = image
                        else:
                            results[image.imgurl] = image
                    success = True
                except Exception as e:
                    logger.warning(f"Failed to parse image item: {e}")
                    continue
            return [x for x in results.values()]
        except Exception as e:
            response_text = response.text if response and response.text else None
            logger.error(f'image_search_fail, Error: {e}')
            time.sleep(random.uniform(0.1, 1))
        finally:
            cost_time = int((time.perf_counter() - start_time) * 1000)
    return []

@register_tool('image_search', allow_overwrite=True)
class ImageSearch(BaseTool):
    name = 'image_search'
    description = 'Image search engine, input the image and search for similar images with image information.'
    parameters = {
        'type': 'object',
        'properties': {
            'img_idx': {
                'type': 'number',
                'description': 'The index of the image (starting from 0)'
            }
        },
        'required': ['img_idx']
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        image_id = int(params['img_idx'])
        images =  extract_images_from_messages(kwargs.get('messages', []))
        if not images:
            return 'Error: no images found in the messages.'
        if image_id >= len(images):
            image_id = len(images) - 1

        image_url = images[image_id]
        try:
            search_results = serper_search(image_url=image_url, check_accessibility=True)
            content = []
            for i, r in enumerate(search_results):

                txt = f'[{str(i+1)}] "{r.imgurl}" {r.title}\n{r.content}'
                txt = txt.strip('\n')
                if txt:
                    content.append(ContentItem(text=txt))
                if r.imgurl:
                    content.append(ContentItem(image=r.imgurl))
            return content
        except Exception as e:
            logger.info(f'Exception in ImageSearch.call: {repr(e)}')
            content = []
        return content


def check_image_url_accessibility(url: str, timeout: int = 10) -> Tuple[str, bool]:
    """
    Check if an image URL is accessible (synchronous version)

    Args:
        url: Image URL to check
        timeout: Request timeout in seconds

    Returns:
        Tuple[str, bool]: A tuple containing the URL and a boolean indicating if it's accessible (True if status is 200)
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return url, response.status_code == 200
    except Exception as e:
        logger.debug(f"Image URL not accessible: {url}, error: {e}")
        return url, False


if __name__ == '__main__':
    print(ImageSearch().call(
        params={'img_idx': 0},
        messages=[
            Message(
                role='user',
                content=[
                    ContentItem(
                        image=
                        'https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg')
                ])
        ]))

