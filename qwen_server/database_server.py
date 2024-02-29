import json
import multiprocessing
import os
from pathlib import Path

try:
    import add_qwen_libs  # NOQA
except ImportError:
    pass
import json5
import jsonlines
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from qwen_agent.log import logger
from qwen_agent.memory import Memory
from qwen_agent.utils.utils import get_local_ip, hash_sha256, save_text_to_file
from qwen_server.schema import GlobalConfig
from qwen_server.utils import (rm_browsing_meta_data, save_browsing_meta_data,
                               save_history)

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
    'http://' + get_local_ip() + ':' +
    str(server_config.server.workstation_port),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.mount('/static',
          StaticFiles(directory=server_config.path.code_interpreter_ws),
          name='static')

cache_file_popup_url = os.path.join(server_config.path.work_space_root,
                                    'popup_url.jsonl')
meta_file = os.path.join(server_config.path.work_space_root, 'meta_data.jsonl')
history_dir = os.path.join(server_config.path.work_space_root, 'history')


def update_pop_url(url: str):
    if not url.lower().endswith('.pdf'):
        url = os.path.join(server_config.path.download_root, hash_sha256(url))
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
    if page_content and not url.lower().endswith('.pdf'):
        # map to local url
        url = os.path.join(server_config.path.download_root, hash_sha256(url))
        save_browsing_meta_data(url, '[CACHING]', meta_file)
        # rm history
        save_history(None, url, history_dir)
        save_text_to_file(url, page_content)
    else:
        save_browsing_meta_data(url, '[CACHING]', meta_file)
        # rm history
        save_history(None, url, history_dir)
    try:
        *_, last = mem.run([{
            'role': 'user',
            'content': [{
                'file': url
            }]
        }],
                           ignore_cache=True)
        data = last[-1]['content']
        if isinstance(data, str):
            data = json5.loads(data)
        assert len(data) == 1
        title = data[-1]['title']
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
        cache_obj = multiprocessing.Process(target=cache_page, kwargs=data)
        cache_obj.start()
        # rsp = cache_data(data, cache_file)
        rsp = 'caching'
    elif msg_type == 'pop_url':
        # What a misleading name! pop_url actually means add_url. pop is referring to the pop_up ui.
        rsp = update_pop_url(data['url'])
    else:
        raise NotImplementedError

    return JSONResponse(content=rsp)


if __name__ == '__main__':
    uvicorn.run(app='database_server:app',
                host=server_config.server.server_host,
                port=server_config.server.fast_api_port)
