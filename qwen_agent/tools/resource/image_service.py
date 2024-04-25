import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

origins = ['http://127.0.0.1:7860']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# TODO: This is buggy if workspace is modified. To be removed.
app.mount(
    '/static',
    StaticFiles(directory=os.path.abspath('workspace/tools/code_interpreter/')),
    name='static',
)

if __name__ == '__main__':
    uvicorn.run(app='image_service:app', port=7865)
