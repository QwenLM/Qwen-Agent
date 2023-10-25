import multiprocessing
import os
import sys

import add_qwen_libs  # NOQA
import jsonlines
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from qwen_server import server_config
from qwen_server.utils import extract_and_cache_document

prompt_lan = sys.argv[1]
llm_name = sys.argv[2]
max_ref_token = int(sys.argv[3])
workstation_port = int(sys.argv[4])
model_server = sys.argv[5]
api_key = sys.argv[6]
server_host = sys.argv[7]

app = FastAPI()

origins = [
    'http://127.0.0.1:' + str(workstation_port),
    'http://localhost:' + str(workstation_port),
    'http://0.0.0.0:' + str(workstation_port),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.mount('/static',
          StaticFiles(directory=server_config.code_interpreter_ws),
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


def update_addr_for_figure(address):
    new_line = {'address': address}

    with jsonlines.open(server_config.address_file, mode='w') as writer:
        writer.write(new_line)

    response = 'Update Address'
    print('Update Address')
    return response


@app.post('/endpoint')
async def web_listening(request: Request):
    data = await request.json()
    msg_type = data['task']

    cache_file_popup_url = os.path.join(server_config.cache_root,
                                        server_config.url_file)
    cache_file = os.path.join(server_config.cache_root,
                              server_config.browser_cache_file)

    if msg_type == 'change_checkbox':
        rsp = change_checkbox_state(data['ckid'], cache_file)
    elif msg_type == 'cache':
        cache_obj = multiprocessing.Process(target=extract_and_cache_document,
                                            args=(data, cache_file))
        cache_obj.start()
        # rsp = cache_data(data, cache_file)
        rsp = 'caching'
    elif msg_type == 'pop_url':
        # What a misleading name! pop_url actually means add_url. pop is referring to the pop_up ui.
        rsp = update_pop_url(data, cache_file_popup_url)
    elif msg_type == 'set_addr':
        rsp = update_addr_for_figure(data['addr'])
    else:
        raise NotImplementedError

    return JSONResponse(content=rsp)


if __name__ == '__main__':
    uvicorn.run(app='database_server:app',
                host=server_host,
                port=server_config.fast_api_port,
                reload=True)
