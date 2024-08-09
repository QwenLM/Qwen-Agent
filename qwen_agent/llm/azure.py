import copy
import logging
import os
from pprint import pformat
from typing import Dict, Iterator, List, Optional

import openai

from openai import OpenAIError

from qwen_agent.llm.base import ModelServiceError, register_llm
from qwen_agent.llm.function_calling import BaseFnCallModel
from qwen_agent.llm.schema import ASSISTANT, Message
from qwen_agent.log import logger


@register_llm('azure')
class TextChatAtAZURE(BaseFnCallModel):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.model = self.model or 'gpt-3.5-turbo'
        cfg = cfg or {}

        api_base = cfg.get(
            'api_base',
            cfg.get(
                'base_url',
                cfg.get('model_server', cfg.get('azure_endpoint','')),
            ),
        ).strip()

        api_key = cfg.get('api_key', '')
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY', 'EMPTY')
        api_key = api_key.strip()
        
        api_version = cfg.get('api_version','2024-06-01')
        
        api_kwargs = {}
        if api_base:
            api_kwargs['azure_endpoint'] = api_base
        if api_key:
            api_kwargs['api_key'] = api_key
        if api_version:
            api_kwargs['api_version'] = api_version
        

        def _chat_complete_create(*args, **kwargs):
            # OpenAI API v1 does not allow the following args, must pass by extra_body
            extra_params = ['top_k', 'repetition_penalty']
            if any((k in kwargs) for k in extra_params):
                kwargs['extra_body'] = copy.deepcopy(kwargs.get('extra_body', {}))
                for k in extra_params:
                    if k in kwargs:
                        kwargs['extra_body'][k] = kwargs.pop(k)
            if 'request_timeout' in kwargs:
                kwargs['timeout'] = kwargs.pop('request_timeout')
            
            client = openai.AzureOpenAI(**api_kwargs)

            # client = openai.OpenAI(**api_kwargs)
            return client.chat.completions.create(*args, **kwargs)

        self._chat_complete_create = _chat_complete_create

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool,
        generate_cfg: dict,
    ) -> Iterator[List[Message]]:
        messages = [msg.model_dump() for msg in messages]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'LLM Input:\n{pretty_format_messages(messages, indent=2)}')
        try:
            response = self._chat_complete_create(model=self.model, messages=messages, stream=True, **generate_cfg)
            if delta_stream:
                for chunk in response:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'Chunk received: {chunk}')
                    if chunk.choices and hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        yield [Message(ASSISTANT, chunk.choices[0].delta.content)]
            else:
                full_response = ''
                for chunk in response:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'Chunk received: {chunk}')
                    if chunk.choices and hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        yield [Message(ASSISTANT, full_response)]
        except OpenAIError as ex:
            raise ModelServiceError(exception=ex)

    def _chat_no_stream(
        self,
        messages: List[Message],
        generate_cfg: dict,
    ) -> List[Message]:
        messages = [msg.model_dump() for msg in messages]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'LLM Input:\n{pretty_format_messages(messages, indent=2)}')
        try:
            response = self._chat_complete_create(model=self.model, messages=messages, stream=False, **generate_cfg)
            return [Message(ASSISTANT, response.choices[0].message.content)]
        except OpenAIError as ex:
            raise ModelServiceError(exception=ex)


def pretty_format_messages(messages: List[dict], indent: int = 2) -> str:
    messages_show = []
    for msg in messages:
        assert isinstance(msg, dict)
        msg_show = copy.deepcopy(msg)
        if isinstance(msg['content'], list):
            content = []
            for item in msg['content']:
                (t, v), = item.items()
                if (t != 'text') and v.startswith('data:'):
                    v = v[:64] + ' ...'
                content.append({t: v})
        else:
            content = msg['content']
        msg_show['content'] = content
        messages_show.append(msg_show)
    return pformat(messages_show, indent=indent)