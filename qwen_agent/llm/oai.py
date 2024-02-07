import os
from typing import Dict, Iterator, List, Optional

import openai

from qwen_agent.llm.base import register_llm
from qwen_agent.llm.text_base import BaseTextChatModel

from .schema import ASSISTANT, Message


@register_llm('oai')
class TextChatAtOAI(BaseTextChatModel):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)

        self.model = self.cfg.get('model', 'Qwen')
        if 'model_server' in self.cfg and self.cfg['model_server'].strip(
        ).lower() != 'openai':
            openai.api_base = self.cfg['model_server']
        if 'api_key' in cfg and cfg['api_key'].strip():
            openai.api_key = cfg['api_key']
        else:
            openai.api_key = os.getenv('OPENAI_API_KEY', 'None')

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool = False,
    ) -> Iterator[List[Message]]:
        messages = [msg.model_dump() for msg in messages]
        response = openai.ChatCompletion.create(model=self.model,
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
        response = openai.ChatCompletion.create(model=self.model,
                                                messages=messages,
                                                stream=False,
                                                **self.generate_cfg)
        # TODO: error handling
        return [Message(ASSISTANT, response.choices[0].message.content)]
