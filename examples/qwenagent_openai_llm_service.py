# -*- coding:utf-8 -*-
# 版本信息
# qwen-agent                               0.0.15

import os
import re
import sys
from qwen_agent.llm import get_chat_model
from fastapi import FastAPI, Header  # , UploadFile, File, Form
from fastapi.responses import StreamingResponse
import logging
from logging.handlers import RotatingFileHandler
from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional, Union

import json
import uuid
import time

logger = logging.getLogger('')
logfile = './qwenagent.log'
rthandler = RotatingFileHandler(logfile, maxBytes=20 * 1024 * 1024, backupCount=10, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
rthandler.setFormatter(formatter)
logger.addHandler(rthandler)
logger.setLevel(logging.INFO)


# OPENAI_API_BASE = 'https://api.openai.com/v1'
model_url = os.environ.get('OPENAI_API_BASE')

def get_llm(model_name, model_url, api_key, temperature=0):
    logger.info(f'model_name={model_name}')
    logger.info(f'model_url={model_url}')
    logger.info(f'temperature={temperature}')
    try:
        llm = get_chat_model({
            'model': model_name,
            'model_server': model_url,
            'api_key': api_key,
            'generate_cfg': {
                'top_p': 0.75,
                'max_input_tokens': 36000,
                'temperature': temperature
            }
        })
        return llm
    except Exception as e:
        msg = f'error in get_llm:{e}'
        logger.error(msg)
        return None

app = FastAPI()

class ChatMessage(BaseModel):
    role: str = Field(..., title='Role name')
    content: Union[str, List[Dict[str, str]]] = Field(...,
                                                      title='Message content')
    tool_calls: Optional[List[Dict]] = Field(None, title='Tool calls')

class ChatCompletionRequest(BaseModel):
    model: str = Field(..., title='Model name')
    messages: List[ChatMessage]
    tools: Optional[List[Dict]] = Field(None, title='Tools config')
    tool_choice: Optional[str] = Field('auto', title='tool usage choice')
    temperature: Optional[float] = Field(0.1, title='temperature')
    stream: Optional[bool] = Field(False, title='Stream output')
    user: str = Field('default_user', title='User name')

class DeltaMessage(BaseModel):
    role: str = Field(None, title='Role name')
    content: str = Field(None, title='Message content')

class ChatCompletionResponseStreamChoice(BaseModel):
    index: int = Field(..., title='Index of the choice')
    delta: DeltaMessage = Field(..., title='Chat message')
    finish_reason: str = Field(None, title='Finish reason')

class ChatCompletionResponseChoice(BaseModel):
    index: int = Field(..., title='Index of the choice')
    message: ChatMessage = Field(..., title='Chat message')
    finish_reason: str = Field(..., title='Finish reason')

class ChatCompletionResponseChoiceFunction(BaseModel):
    index: int = Field(..., title='Index of the choice')
    function: str = Field(..., title='Chat message')
    finish_reason: str = Field(..., title='Finish reason')

class Usage(BaseModel):
    prompt_tokens: int = Field(-1, title='Prompt tokens consumed')
    completion_tokens: int = Field(-1, title='Completion tokens consumed')
    total_tokens: int = Field(-1, title='Total tokens consumed')

class ChatCompletionResponse(BaseModel):
    id: str = Field(..., title='Unique id for chat completion')
    choices: List[Union[ChatCompletionResponseChoice,
                        ChatCompletionResponseStreamChoice]]
    created: Optional[int] = Field(default_factory=lambda: int(time.time()))
    model: str = Field(..., title='Model name')
    system_fingerprint: str = Field(None, title='Cuurently request id')
    object: Literal['chat.completion', 'chat.completion.chunk'] = Field(
        'chat.completion', title='Object type')
    usage: Optional[Usage] = Field(
        default=Usage(), title='Token usage information')

def stream_choice_wrapper(response, model, request_id):
    last_msg = ''
    function = 0
    try:
        for chunk in response:
            if 'function_call' in chunk[0].keys():
                function = 1
                continue
            chunk_msg = chunk[0]['content']
            new_msg = chunk_msg[len(last_msg):]
            last_msg = chunk_msg
            choices = ChatCompletionResponseStreamChoice(
                index=0,
                delta=DeltaMessage(role='assistant', content=new_msg),
            )
            chunk = ChatCompletionResponse(
                id=request_id,
                object='chat.completion.chunk',
                choices=[choices],
                model=model)
            data = chunk.model_dump_json(exclude_unset=True)
            yield f'data: {data}\n\n'
        if function == 1:
            res = chunk[0]
            result = result_build(res, model, request_id)
            data = json.dumps(result)
            yield f'data: {data}\n\n'
            yield 'data: [DONE]\n\n'
        else:
            choices = ChatCompletionResponseStreamChoice(
                index=0, delta=DeltaMessage(), finish_reason='stop')
            chunk = ChatCompletionResponse(
                id=request_id,
                object='chat.completion.chunk',
                choices=[choices],
                model=model,
                usage=None)
            data = chunk.model_dump_json(exclude_unset=True)
            yield f'data: {data}\n\n'
            yield 'data: [DONE]\n\n'
    except Exception as e:
        logger.error(f'error in stream_choice_wrapper: {e}')
        print(f'error in stream_choice_wrapper: {e}')
        search_obj = re.search(r"\{.*\}", str(e), flags=re.S)
        if search_obj is None:
            data = json.dumps({
                "id": "",
                "object": "error",
                "message": [{
                    "loc": ('body'),
                    "msg": "{}".format(e),
                    "type": ""
                }],
                'code': 40001
            })
            yield f'data: {data}\n\n'
            yield 'data: [DONE]\n\n'

        valid_str = search_obj.group()
        valid_str = valid_str.replace('null', '\'null\'').replace('None', '\'null\'')
        re_dict = json.dumps(eval(valid_str))
        yield f'data: {re_dict}\n\n'
        yield 'data: [DONE]\n\n'

@app.post('/v1/chat/completions')
def get_entity(chat_request: ChatCompletionRequest, authorization: str = Header(None)):
    try:
        request_id = f"chatcmpl-{uuid.uuid4()}"
        user = chat_request.user
        print(f'user={user}')

        model = chat_request.model
        print(f'model={model}')
        stream = chat_request.stream
        temperature = chat_request.temperature
        api_key = authorization[7:] if authorization else 'EMPTY'
        messages_s = chat_request.messages
        messages = []
        for msg_ in messages_s:
            msg = msg_.dict()
            if msg['role'] == 'tool':
                msg['role'] = 'function'
            if msg['content'] is None:
                msg['content'] = ''
            messages.append(msg)
        print(f'messages={messages}')

        functions = []

        if chat_request.tools:
            tools = chat_request.tools
            for tool in tools:
                name = tool['function']['name']
                description = tool['function']['description']
                parameters = tool['function']['parameters']
                functions.append({
                    'name': name,
                    'description': description,
                    'parameters': parameters,
                })
        logger.info(f'messages={messages}\n')
        logger.info(f'functions={functions}\n')
        llm = get_llm(model, model_url, api_key, temperature)
        if stream:
            responses = llm.chat(
                messages=messages,
                functions=functions,
                stream=True,
            )
            stream_chat_response = stream_choice_wrapper(responses, model, request_id)
            return StreamingResponse(stream_chat_response, media_type='text/event-stream')
        else:
            logger.info(f"not stream")
            try:
                responses = llm.chat(
                    messages=messages,
                    functions=functions,
                    stream=False,
                )
            except Exception as e:
                logger.error(f'error when chat: {e}')
                search_obj = re.search(r"\{.*\}", str(e), flags=re.S)
                if search_obj is None:
                    return {
                        "id": "",
                        "object": "error",
                        "message": [{
                            "loc": ('body'),
                            "msg": "{}".format(e),
                            "type": ""
                        }],
                        'code': 40001
                    }

                valid_str = search_obj.group()
                valid_str = valid_str.replace('null', '\'null\'').replace('None', '\'null\'')
                re_dict = eval(valid_str)
                return re_dict

            logger.info(f'responses={responses}\n')
            if len(responses) == 0:
                res = {'role': 'assistant', 'content': ''}
            else:
                res = responses[0]
            result = result_build(res, model, request_id)
            return result
    except Exception as e:
        logger.error('error in get_entity : {e}')
        return {
                    "id": "",
                    "object": "error",
                    "message": [{
                            "loc": ('body'),
                            "msg": "{}".format(e),
                            "type": ""
                        }],
                    'code': 40001
                }
    # return {}
def result_build(res, model_name, request_id):
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    # print(123, prompt_tokens, completion_tokens, total_tokens)

    message_ret = {}
    message_ret['role'] = res['role']
    # print(22222, res['content'])
    if res['content'] is None:
        message_ret['content'] = ''
    else:
        message_ret['content'] = res['content']
    # message_ret['content'] = '' if res['content'] is None else res['content']
    tool_calls = [{}]
    if 'function_call' in res.keys():
        function_call = res['function_call']
        tool_calls[0]['id'] = f"call_{uuid.uuid4()}"
        tool_calls[0]['type'] = "function"
        tool_calls[0]['function'] = function_call
        message_ret['tool_calls'] = tool_calls
    result = {
        "choices": [
            {
                "finish_reason": "stop",
                "index": 0,
                "message": message_ret
            }
        ],
        "created": int(time.time()),
        "model": model_name,
        "object": "chat.completion",
        "id": request_id,
        "usage": {
            "completion_tokens": completion_tokens,
            "prompt_tokens": prompt_tokens,
            "total_tokens": total_tokens
        }
    }
    logger.info(f'result={result}\n')

    return result


if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=8010, debug=False)
    import uvicorn
    uvicorn.run(app=app, host='0.0.0.0', port=8008)
