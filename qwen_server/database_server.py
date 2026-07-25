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
import multiprocessing
import os
from pathlib import Path
from urllib.parse import urlparse

import jsonlines
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    import add_qwen_libs  # NOQA
except ImportError:
    pass

from qwen_agent.log import logger
from qwen_agent.memory import Memory
from qwen_agent.utils.utils import (get_basename_from_url, get_file_type, get_local_ip, hash_sha256,
                                    sanitize_chrome_file_path, save_text_to_file)
from qwen_server.schema import GlobalConfig
from qwen_server.utils import rm_browsing_meta_data, save_browsing_meta_data, save_history

# Read config
with open(Path(__file__).resolve().parent / 'server_config.json', 'r') as f:
    server_config = json.load(f)
    server_config = GlobalConfig(**server_config)

# This APP only requires storage capacity, so using the memory module alone
mem = Memory()

app = FastAPI()

logger.info(get_local_ip())
origins = [
    'http://127.0.0.1:' + str(server_config.server.workstation_port),
    'http://localhost:' + str(server_config.server.workstation_port),
    'http://0.0.0.0:' + str(server_config.server.workstation_port),
    'http://' + get_local_ip() + ':' + str(server_config.server.workstation_port),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.mount('/static', StaticFiles(directory=server_config.path.code_interpreter_ws), name='static')

cache_file_popup_url = os.path.join(server_config.path.work_space_root, 'popup_url.jsonl')
meta_file = os.path.join(server_config.path.work_space_root, 'meta_data.jsonl')
history_dir = os.path.join(server_config.path.work_space_root, 'history')

# This endpoint is unauthenticated, so a request url is only allowed to reach the document parser
# when it is a web page or a file the server itself owns. Anything else is an attempt to make the
# parser read an arbitrary host file. Local files that the user picked are added by the
# workstation UI, which calls Memory directly and does not go through this server.
ALLOWED_URL_SCHEMES = ('http', 'https')
ALLOWED_LOCAL_ROOTS = (
    server_config.path.work_space_root,
    server_config.path.download_root,
    server_config.path.code_interpreter_ws,
)
# Set QWEN_AGENT_ALLOW_LOCAL_FILE_CACHE=true to keep caching local files outside the workspace,
# such as a 'file:///...' tab opened in the browser. Only do this if the endpoint is unreachable
# by anyone but you: it lets a caller read any file the server can read.
ALLOW_LOCAL_FILE_CACHE = os.getenv('QWEN_AGENT_ALLOW_LOCAL_FILE_CACHE', '').strip().lower() in ('1', 'true', 'yes')


def is_within_directory(path: str, directory: str) -> bool:
    try:
        directory = os.path.realpath(directory)
        return os.path.commonpath([os.path.realpath(path), directory]) == directory
    except ValueError:
        # Raised for e.g. paths on different Windows drives, which are never within the workspace.
        return False


def validate_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError('The url must be a non-empty string.')
    if ALLOW_LOCAL_FILE_CACHE or urlparse(url).scheme.lower() in ALLOWED_URL_SCHEMES:
        return url
    # Resolve the same way the parser does, so that the check covers the path that is really read.
    local_path = sanitize_chrome_file_path(url)
    if any(is_within_directory(local_path, root) for root in ALLOWED_LOCAL_ROOTS):
        return url
    raise ValueError(f'Refusing to read {url}: this endpoint only accepts http(s) urls and files '
                     'under the server workspace. Set QWEN_AGENT_ALLOW_LOCAL_FILE_CACHE=true to '
                     'allow caching other local files.')


def update_pop_url(url: str):
    if not get_file_type(url) in ['pdf', 'docx', 'pptx', 'txt']:
        url = os.path.join(server_config.path.download_root, hash_sha256(url), get_basename_from_url(url))
    new_line = {'url': url}

    with jsonlines.open(cache_file_popup_url, mode='w') as writer:
        writer.write(new_line)

    return 'Update URL'


def change_checkbox_state(key):
    with open(meta_file, 'r', encoding='utf-8') as file:
        meta_info = json.load(file)
    meta_info[key[3:]]['checked'] = (not meta_info[key[3:]]['checked'])
    with open(meta_file, 'w', encoding='utf-8') as file:
        json.dump(meta_info, file, indent=4)
    return {'result': 'changed'}


def cache_page(**kwargs):
    url = kwargs.get('url', '')

    page_content = kwargs.get('content', '')
    if page_content and not get_file_type(url) in ['pdf', 'docx', 'pptx', 'txt']:
        # map to local url
        os.makedirs(os.path.join(server_config.path.download_root, hash_sha256(url)), exist_ok=True)
        url = os.path.join(server_config.path.download_root, hash_sha256(url), get_basename_from_url(url))
        save_browsing_meta_data(url, '[CACHING]', meta_file)
        # rm history
        save_history(None, url, history_dir)
        save_text_to_file(url, page_content)
    else:
        save_browsing_meta_data(url, '[CACHING]', meta_file)
        # rm history
        save_history(None, url, history_dir)
    try:
        *_, last = mem.run([{'role': 'user', 'content': [{'file': url}]}])
        title = get_basename_from_url(url)
        save_browsing_meta_data(url, title, meta_file)
    except Exception:
        rm_browsing_meta_data(url, meta_file)


@app.post('/endpoint')
async def web_listening(request: Request):
    data = await request.json()
    msg_type = data['task']

    if msg_type == 'change_checkbox':
        rsp = change_checkbox_state(data['ckid'])
    elif msg_type == 'cache':
        try:
            data['url'] = validate_url(data.get('url', ''))
        except ValueError as ex:
            logger.warning(str(ex))
            return JSONResponse(status_code=400, content=str(ex))
        cache_obj = multiprocessing.Process(target=cache_page, kwargs=data)
        cache_obj.start()
        # rsp = cache_data(data, cache_file)
        rsp = 'caching'
    elif msg_type == 'pop_url':
        # What a misleading name! pop_url actually means add_url. pop is referring to the pop_up ui.
        try:
            url = validate_url(data.get('url', ''))
        except ValueError as ex:
            logger.warning(str(ex))
            return JSONResponse(status_code=400, content=str(ex))
        rsp = update_pop_url(url)
    else:
        raise NotImplementedError

    return JSONResponse(content=rsp)


if __name__ == '__main__':
    uvicorn.run(app='database_server:app',
                host=server_config.server.server_host,
                port=server_config.server.fast_api_port)
