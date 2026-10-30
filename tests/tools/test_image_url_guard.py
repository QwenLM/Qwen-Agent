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
import socket
from io import BytesIO

import pytest
import requests
from PIL import Image

from qwen_agent.llm.schema import ContentItem, Message
from qwen_agent.tools.image_zoom_in_qwen3vl import ImageZoomInToolQwen3VL
from qwen_agent.utils.output_beautify import multimodal_typewriter_print
from qwen_agent.utils.url_guard import ALLOW_PRIVATE_NETWORK_ENV, DEFAULT_TIMEOUT_SECONDS


@pytest.fixture
def image_http(monkeypatch):
    """Keep Requests redirect handling real while replacing network transport."""
    monkeypatch.delenv(ALLOW_PRIVATE_NETWORK_ENV, raising=False)
    buffer = BytesIO()
    Image.new('RGB', (64, 64), 'red').save(buffer, format='PNG')
    png = buffer.getvalue()
    routes = {}
    calls = []

    def resolve(host, *args, **kwargs):
        ip = '93.184.216.34' if host == 'example.com' else host
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 0))]

    def send(adapter, request, **kwargs):
        calls.append((request.url, kwargs))
        status, location = routes.get(request.url, (200, None))
        response = requests.Response()
        response.status_code = status
        response.url = request.url
        response.request = request
        response.raw = BytesIO(png)
        if location:
            response.headers['Location'] = location
        return response

    monkeypatch.setattr(socket, 'getaddrinfo', resolve)
    monkeypatch.setattr('requests.adapters.HTTPAdapter.send', send)
    return routes, calls, png


@pytest.fixture(params=['zoom', 'notebook'])
def render_image(request, monkeypatch, tmp_path):
    """Return the actual decoded images emitted by either production entry point."""
    if request.param == 'zoom':
        tool = ImageZoomInToolQwen3VL({'work_dir': str(tmp_path / 'zoom')})

        def render(source):
            result = tool.call({
                'bbox_2d': [0, 0, 1000, 1000],
                'label': 'image',
                'img_idx': 0
            },
                               messages=[Message(role='user', content=[ContentItem(image=source)])])
            return [Image.open(item.image) for item in result if item.image]
    else:
        display = pytest.importorskip('IPython.display')
        displayed = []
        monkeypatch.setattr(display, 'display', displayed.append)

        def render(source):
            displayed.clear()
            multimodal_typewriter_print([{'role': 'function', 'name': 'image_tool', 'content': [{'image': source}]}])
            return displayed

    return render


@pytest.mark.parametrize('url', ['http://127.0.0.1/image.png', 'http://169.254.169.254/image.png'])
def test_image_download_blocks_private_addresses(render_image, image_http, url):
    _, calls, _ = image_http
    assert render_image(url) == []
    assert calls == []


def test_image_download_blocks_redirect_to_private_address(render_image, image_http):
    routes, calls, _ = image_http
    url = 'https://example.com/image.png'
    routes[url] = (302, 'http://127.0.0.1/image.png')
    assert render_image(url) == []
    assert [call[0] for call in calls] == [url]


@pytest.mark.parametrize('redirect', [False, True])
def test_image_download_accepts_public_images(render_image, image_http, redirect):
    routes, calls, _ = image_http
    url = 'https://example.com/image.png'
    if redirect:
        routes[url] = (302, '/redirected.png')
    images = render_image(url)
    assert len(images) == 1
    assert images[0].getpixel((0, 0)) == (255, 0, 0)
    expected_urls = [url, 'https://example.com/redirected.png'] if redirect else [url]
    assert [call[0] for call in calls] == expected_urls
    assert all(call[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS for call in calls)


def test_image_download_rejects_http_errors(render_image, image_http):
    routes, _, _ = image_http
    url = 'https://example.com/image.png'
    routes[url] = (404, None)
    assert render_image(url) == []


def test_image_download_keeps_local_images(render_image, image_http, tmp_path):
    _, calls, png = image_http
    path = tmp_path / 'local.png'
    path.write_bytes(png)
    images = render_image(str(path))
    assert len(images) == 1
    assert images[0].getpixel((0, 0)) == (255, 0, 0)
    assert calls == []


def test_image_download_supports_private_network_opt_out(render_image, image_http, monkeypatch):
    _, calls, _ = image_http
    monkeypatch.setenv(ALLOW_PRIVATE_NETWORK_ENV, '1')
    url = 'http://127.0.0.1/image.png'
    images = render_image(url)
    assert len(images) == 1
    assert images[0].getpixel((0, 0)) == (255, 0, 0)
    assert [call[0] for call in calls] == [url]
