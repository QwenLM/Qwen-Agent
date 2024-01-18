import os
from typing import Dict, Iterator, List, Optional, Union

import openai

from qwen_agent.llm.base import BaseChatModel
from qwen_agent.log import logger


class QwenChatAsOAI(BaseChatModel):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.model = self.cfg.get('model', '')
        if 'model_server' in self.cfg and self.cfg['model_server'].strip(
        ).lower() != 'openai':
            openai.api_base = self.cfg['model_server']
        openai.api_key = os.getenv('OPENAI_API_KEY',
                                   default=self.cfg.get('api_key', ''))

    def _chat_stream(
        self,
        messages: List[Dict],
        stop: Optional[List[str]] = None,
        delta_stream: bool = False,
    ) -> Iterator[List[Dict]]:
        response = openai.ChatCompletion.create(model=self.model,
                                                messages=messages,
                                                stop=stop,
                                                stream=True,
                                                **self.generate_cfg)
        # TODO: error handling
        if delta_stream:
            for chunk in response:
                if hasattr(chunk.choices[0].delta, 'content'):
                    yield self._wrapper_text_to_message_list(
                        chunk.choices[0].delta.content)
        else:
            full_response = ''
            for chunk in response:
                if hasattr(chunk.choices[0].delta, 'content'):
                    full_response += chunk.choices[0].delta.content
                    yield self._wrapper_text_to_message_list(full_response)

    def _chat_no_stream(self,
                        messages: List[Dict],
                        stop: Optional[List[str]] = None) -> List[Dict]:
        response = openai.ChatCompletion.create(model=self.model,
                                                messages=messages,
                                                stop=stop,
                                                stream=False,
                                                **self.generate_cfg)
        # TODO: error handling
        return self._wrapper_text_to_message_list(
            response.choices[0].message.content)

    def chat_with_functions(
            self,
            messages: List[Dict],
            functions: Optional[List[Dict]] = None,
            stop: Optional[List[str]] = None,
            stream: bool = True,
            delta_stream: bool = False
    ) -> Union[List[Dict], Iterator[List[Dict]]]:
        assert not delta_stream, 'qwenoai only supports delta_stream=False for function call now'
        if stream:
            # Todo: support streaming
            # Temporary plan
            logger.warning(
                'This method does not support stream=True, Simulate using stream=False!'
            )
        logger.debug('==== Inputted messages ===')
        logger.debug(messages)
        logger.debug(functions)

        response = openai.ChatCompletion.create(model=self.model,
                                                messages=messages,
                                                functions=functions,
                                                **self.generate_cfg)
        # TODO: error handling
        if stream:
            return self._wrapper_output_iterator([response.choices[0].message])
        else:
            return [response.choices[0].message]

    def _wrapper_output_iterator(self, message):
        yield message
