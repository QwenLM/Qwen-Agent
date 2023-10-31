import json
import multiprocessing
import os
from pathlib import Path

import add_qwen_libs  # NOQA
import jsonlines
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from qwen_agent.log import logger
from qwen_agent.utils.utils import get_local_ip
from qwen_server.schema import GlobalConfig
from qwen_server.utils import extract_and_cache_document

# Read config
with open(Path(__file__).resolve().parent / 'server_config.json', 'r') as f:
    server_config = json.load(f)
    server_config = GlobalConfig(**server_config)

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


def update_pop_url(data, cache_file_popup_url):
    new_line = {'url': data['url']}

    with jsonlines.open(cache_file_popup_url, mode='w') as writer:
        writer.write(new_line)

    response = 'Update URL'
    return response


def change_checkbox_state(text, cache_file):
    if not os.path.exists(cache_file):
        return {'result': 'no file'}
    lines = []
    for line in jsonlines.open(cache_file):
        if line['url'] == text[3:]:
            if line['checked']:
                line['checked'] = False
            else:
                line['checked'] = True
        lines.append(line)

    with jsonlines.open(cache_file, mode='w') as writer:
        for new_line in lines:
            writer.write(new_line)

    return {'result': 'changed'}


@app.post('/endpoint')
async def web_listening(request: Request):
    data = await request.json()
    msg_type = data['task']

    cache_file_popup_url = os.path.join(server_config.path.cache_root,
                                        'popup_url.jsonl')
    cache_file = os.path.join(server_config.path.cache_root, 'browse.jsonl')

    if msg_type == 'change_checkbox':
        rsp = change_checkbox_state(data['ckid'], cache_file)
    elif msg_type == 'cache':
        cache_obj = multiprocessing.Process(
            target=extract_and_cache_document,
            args=(data, cache_file, server_config.path.cache_root))
        cache_obj.start()
        # rsp = cache_data(data, cache_file)
        rsp = 'caching'
    elif msg_type == 'pop_url':
        # What a misleading name! pop_url actually means add_url. pop is referring to the pop_up ui.
        rsp = update_pop_url(data, cache_file_popup_url)
    else:
        raise NotImplementedError

    return JSONResponse(content=rsp)


if __name__ == '__main__':
    uvicorn.run(app='database_server:app',
                host=server_config.server.server_host,
                port=server_config.server.fast_api_port,
                reload=True)
