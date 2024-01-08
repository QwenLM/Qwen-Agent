import json
import multiprocessing
from pathlib import Path

import add_qwen_libs  # NOQA
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from qwen_agent.agents import DocQAAgent
from qwen_agent.log import logger
from qwen_agent.utils.utils import get_local_ip, print_traceback
from qwen_server.schema import GlobalConfig

# Read config
with open(Path(__file__).resolve().parent / 'server_config.json', 'r') as f:
    server_config = json.load(f)
    server_config = GlobalConfig(**server_config)

assistant = DocQAAgent(function_list=['doc_parser'],
                       llm_config=False,
                       storage_path=server_config.path.database_root)

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


def update_pop_url(url: str):
    msg = assistant.mem.db.put('browsing_url', url)
    if msg == 'SUCCESS':
        response = 'Updated URL'
    else:
        print_traceback()
        response = 'Failed to update URL'
    return response


def change_checkbox_state(key):
    meta_info = json.loads(assistant.mem.db.get('meta_info'))
    meta_info[key[3:]]['checked'] = (not meta_info[key[3:]]['checked'])
    assistant.mem.db.put('meta_info', json.dumps(meta_info,
                                                 ensure_ascii=False))
    return {'result': 'changed'}


@app.post('/endpoint')
async def web_listening(request: Request):
    data = await request.json()
    msg_type = data['task']

    if msg_type == 'change_checkbox':
        rsp = change_checkbox_state(data['ckid'])
    elif msg_type == 'cache':
        cache_obj = multiprocessing.Process(target=assistant.mem.run,
                                            kwargs=data)
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
                port=server_config.server.fast_api_port,
                reload=True)
