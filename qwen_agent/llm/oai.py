import copy
import os
from typing import Dict, Iterator, List, Optional, Union

import openai

from qwen_agent.llm.base import FnCallNotImplError, register_llm
from qwen_agent.llm.text_base import BaseTextChatModel
from qwen_agent.log import logger
from qwen_agent.utils.utils import print_traceback

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

        self._support_fn_call: Optional[bool] = None

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

    def chat_with_functions(
        self,
        messages: List[Union[Message, Dict]],
        functions: Optional[List[Dict]] = None,
        stream: bool = True,
        delta_stream: bool = False
    ) -> Union[List[Message], Iterator[List[Message]]]:

        if self._support_function_calling():
            return self._chat_with_functions(messages=messages,
                                             functions=functions,
                                             stream=stream,
                                             delta_stream=delta_stream)
        else:
            logger.info(
                'Detected function calls are not supported, using chat format')
            return super().chat_with_functions(messages=messages,
                                               functions=functions,
                                               stream=stream,
                                               delta_stream=delta_stream)

    def _chat_with_functions(
        self,
        messages: List[Union[Message, Dict]],
        functions: Optional[List[Dict]] = None,
        stream: bool = True,
        delta_stream: bool = False
    ) -> Union[List[Message], Iterator[List[Message]]]:
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

        messages = copy.deepcopy(messages)
        messages = [
            Message(**msg) if isinstance(msg, dict) else msg
            for msg in messages
        ]
        messages = self._format_msg_for_llm(messages)

        messages = [msg.model_dump() for msg in messages]
        response = openai.ChatCompletion.create(model=self.model,
                                                messages=messages,
                                                functions=functions,
                                                **self.generate_cfg)
        # TODO: error handling
        if stream:
            return self._postprocess_iterator([response.choices[0].message])
        else:
            return [Message(**response.choices[0].message)]

    def _support_function_calling(self) -> bool:
        if self._support_fn_call is None:
            functions = [{
                'name': 'get_current_weather',
                'description': 'Get the current weather in a given location.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'location': {
                            'type':
                            'string',
                            'description':
                            'The city and state, e.g. San Francisco, CA',
                        },
                        'unit': {
                            'type': 'string',
                            'enum': ['celsius', 'fahrenheit'],
                        },
                    },
                    'required': ['location'],
                },
            }]
            messages = [Message('user', 'What is the weather like in Boston?')]
            self._support_fn_call = False
            try:
                *_, last = self._chat_with_functions(messages=messages,
                                                     functions=functions,
                                                     stream=True)
                response = last[-1]
                if response.function_call:
                    logger.info('Support of function calling is detected.')
                    self._support_fn_call = True
            except FnCallNotImplError:
                pass
            except Exception:  # TODO: more specific
                print_traceback()
        return self._support_fn_call
