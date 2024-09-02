import copy
import os
from typing import Dict, Optional

import openai

from qwen_agent.llm.base import register_llm
from qwen_agent.llm.oai import TextChatAtOAI


@register_llm('azure')
class TextChatAtAzure(TextChatAtOAI):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        cfg = cfg or {}

        api_base = cfg.get(
            'api_base',
            cfg.get(
                'base_url',
                cfg.get('model_server', cfg.get('azure_endpoint', '')),
            ),
        ).strip()

        api_key = cfg.get('api_key', '')
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY', 'EMPTY')
        api_key = api_key.strip()

        api_version = cfg.get('api_version', '2024-06-01')

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
