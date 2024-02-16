import os
from pprint import pformat
from typing import Dict, Iterator, List, Optional

import openai

from qwen_agent.llm.base import register_llm
from qwen_agent.llm.text_base import BaseTextChatModel
from qwen_agent.log import logger

from .schema import ASSISTANT, Message


@register_llm('oai')
class TextChatAtOAI(BaseTextChatModel):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.model = self.cfg.get('model', 'gpt-3.5-turbo')

        api_base = self.cfg.get(
            'api_base',
            self.cfg.get(
                'base_url',
                self.cfg.get('model_server', ''),
            ),
        ).strip()

        api_key = self.cfg.get('api_key', '').strip()
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY', 'EMPTY').strip()

        if openai.__version__.startswith('0.'):
            if api_base:
                openai.api_base = api_base
            if api_key:
                openai.api_key = api_key
            self._chat_complete_create = openai.ChatCompletion.create
        else:
            api_kwargs = {}
            if api_base:
                api_kwargs['base_url'] = api_base
            if api_key:
                api_kwargs['api_key'] = api_key

            def _chat_complete_create(*args, **kwargs):
                client = openai.OpenAI(**api_kwargs)
                return client.chat.completions.create(*args, **kwargs)

            self._chat_complete_create = _chat_complete_create

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool = False,
    ) -> Iterator[List[Message]]:
        messages = [msg.model_dump() for msg in messages]
        logger.debug(f'*{pformat(messages, indent=2)}*')
        response = self._chat_complete_create(model=self.model,
                                              messages=messages,
                                              stream=True,
                                              **self.generate_cfg)
        # TODO: error handling
        if delta_stream:
            for chunk in response:
                if hasattr(chunk.choices[0].delta, 'content'):
                    yield [Message(ASSISTANT, chunk.choices[0].delta.content)]
        else:
            full_response = ''
            for chunk in response:
                if hasattr(chunk.choices[0].delta, 'content'):
                    full_response += chunk.choices[0].delta.content
                    yield [Message(ASSISTANT, full_response)]

    def _chat_no_stream(self, messages: List[Message]) -> List[Message]:
        messages = [msg.model_dump() for msg in messages]
        logger.debug(f'*{pformat(messages, indent=2)}*')
        response = self._chat_complete_create(model=self.model,
                                              messages=messages,
                                              stream=False,
                                              **self.generate_cfg)
        # TODO: error handling
        return [Message(ASSISTANT, response.choices[0].message.content)]
