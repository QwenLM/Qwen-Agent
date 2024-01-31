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

app.mount('/static',
          StaticFiles(directory=os.getcwd() + '/workspace/ci_workspace/'),
          name='static')

if __name__ == '__main__':
    uvicorn.run(app='image_service:app', port=7865)
