from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.log import logger
from qwen_agent.utils.utils import print_traceback


class FnCallNotImplError(NotImplementedError):
    pass


class BaseChatModel(ABC):

    def __init__(self):
        self._support_fn_call: Optional[bool] = None

    # It is okay to use the same code to handle the output
    # regardless of whether stream is True or False, as follows:
    # ```py
    # for chunk in chat_model.chat(..., stream=True/False):
    #   response += chunk
    #   yield response
    # ```
    def chat(
        self,
        prompt: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        stop: Optional[List[str]] = None,
        stream: bool = False,
    ) -> Union[str, Iterator[str]]:
        if messages is None:
            assert isinstance(prompt, str)
            messages = [{'role': 'user', 'content': prompt}]
        else:
            assert prompt is None, 'Do not pass prompt and messages at the same time.'
        logger.debug(messages)
        if stream:
            return self._chat_stream(messages, stop=stop)
        else:
            return self._chat_no_stream(messages, stop=stop)

    def support_function_calling(self) -> bool:
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
            messages = [{
                'role': 'user',
                'content': 'What is the weather like in Boston?'
            }]
            self._support_fn_call = False
            try:
                response = self.chat_with_functions(messages=messages,
                                                    functions=functions)
                if response.get('function_call', None):
                    logger.info('Support of function calling is detected.')
                    self._support_fn_call = True
            except FnCallNotImplError:
                pass
            except Exception:  # TODO: more specific
                print_traceback()
        return self._support_fn_call

    def chat_with_functions(self,
                            messages: List[Dict],
                            functions: Optional[List[Dict]] = None) -> Dict:
        raise FnCallNotImplError

    def support_raw_prompt(self) -> bool:
        try:
            if self.chat_with_raw_prompt(prompt='') == '[Do not Support]':
                return False
            else:
                return True
        except Exception:
            return False

    def chat_with_raw_prompt(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
    ) -> str:
        return '[Do not Support]'

    @abstractmethod
    def _chat_stream(
        self,
        messages: List[Dict],
        stop: Optional[List[str]] = None,
    ) -> Iterator[str]:
        raise NotImplementedError

    @abstractmethod
    def _chat_no_stream(
        self,
        messages: List[Dict],
        stop: Optional[List[str]] = None,
    ) -> str:
        raise NotImplementedError
