import os
from typing import Dict, Iterator, List, Optional

import openai

from qwen_agent.llm.base import BaseChatModel


class QwenChatAsOAI(BaseChatModel):

    def __init__(self, model: str, api_key: str, model_server: str):
        super().__init__()
        if model_server.strip().lower() != 'openai':
            openai.api_base = model_server
        openai.api_key = api_key.strip() or os.getenv('OPENAI_API_KEY',
                                                      default='EMPTY')
        self.model = model

    def _chat_stream(
        self,
        messages: List[Dict],
        stop: Optional[List[str]] = None,
    ) -> Iterator[str]:
        response = openai.ChatCompletion.create(model=self.model,
                                                messages=messages,
                                                stop=stop,
                                                stream=True)
        # TODO: error handling
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                yield chunk.choices[0].delta.content

    def _chat_no_stream(
        self,
        messages: List[Dict],
        stop: Optional[List[str]] = None,
    ) -> str:
        response = openai.ChatCompletion.create(model=self.model,
                                                messages=messages,
                                                stop=stop,
                                                stream=False)
        # TODO: error handling
        return response.choices[0].message.content

    def chat_with_functions(self,
                            messages: List[Dict],
                            functions: Optional[List[Dict]] = None) -> Dict:
        if functions:
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=messages,
                                                    functions=functions)
        else:
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=messages)
        # TODO: error handling
        return response.choices[0].message
