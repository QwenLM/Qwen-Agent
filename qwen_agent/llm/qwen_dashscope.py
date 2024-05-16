import os
from http import HTTPStatus
from pprint import pformat
from typing import Dict, Iterator, List, Optional

import dashscope

from qwen_agent.llm.base import ModelServiceError, register_llm
from qwen_agent.llm.schema import ASSISTANT, DEFAULT_SYSTEM_MESSAGE, SYSTEM, USER, Message
from qwen_agent.llm.text_base import BaseTextChatModel
from qwen_agent.log import logger


@register_llm('qwen_dashscope')
class QwenChatAtDS(BaseTextChatModel):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.model = self.model or 'qwen-max'
        initialize_dashscope(cfg)

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool,
        generate_cfg: dict,
    ) -> Iterator[List[Message]]:
        messages = [msg.model_dump() for msg in messages]
        logger.debug(f'*{pformat(messages, indent=2)}*')
        response = dashscope.Generation.call(
            self.model,
            messages=messages,  # noqa
            result_format='message',
            stream=True,
            **generate_cfg)
        if delta_stream:
            return self._delta_stream_output(response)
        else:
            return self._full_stream_output(response)

    def _chat_no_stream(
        self,
        messages: List[Message],
        generate_cfg: dict,
    ) -> List[Message]:
        messages = [msg.model_dump() for msg in messages]
        logger.debug(f'*{pformat(messages, indent=2)}*')
        response = dashscope.Generation.call(
            self.model,
            messages=messages,  # noqa
            result_format='message',
            stream=False,
            **generate_cfg)
        if response.status_code == HTTPStatus.OK:
            return [Message(ASSISTANT, response.output.choices[0].message.content)]
        else:
            raise ModelServiceError(code=response.code, message=response.message)

    def _continue_assistant_response(
        self,
        messages: List[Message],
        generate_cfg: dict,
        stream: bool,
    ) -> Iterator[List[Message]]:
        prompt = self._build_text_completion_prompt(messages)
        logger.debug(f'*{prompt}*')
        response = dashscope.Generation.call(
            self.model,
            prompt=prompt,  # noqa
            result_format='message',
            stream=True,
            use_raw_prompt=True,
            **generate_cfg)
        it = self._full_stream_output(response)
        if stream:
            return it  # streaming the response
        else:
            *_, final_response = it  # return the final response without streaming
            return final_response

    @staticmethod
    def _build_text_completion_prompt(messages: List[Message]) -> str:
        im_start = '<|im_start|>'
        im_end = '<|im_end|>'
        if messages[0].role == SYSTEM:
            sys = messages[0].content
            assert isinstance(sys, str)
            prompt = f'{im_start}{SYSTEM}\n{sys}{im_end}'
        else:
            prompt = f'{im_start}{SYSTEM}\n{DEFAULT_SYSTEM_MESSAGE}{im_end}'
        if messages[-1].role != ASSISTANT:
            messages.append(Message(ASSISTANT, ''))
        for msg in messages:
            assert isinstance(msg.content, str)
            if msg.role == USER:
                query = msg.content.lstrip('\n').rstrip()
                prompt += f'\n{im_start}{USER}\n{query}{im_end}'
            elif msg.role == ASSISTANT:
                response = msg.content.lstrip('\n').rstrip()
                prompt += f'\n{im_start}{ASSISTANT}\n{response}{im_end}'
        assert prompt.endswith(im_end)
        prompt = prompt[:-len(im_end)]
        return prompt

    @staticmethod
    def _delta_stream_output(response) -> Iterator[List[Message]]:
        last_len = 0
        delay_len = 5
        in_delay = False
        text = ''
        for chunk in response:
            if chunk.status_code == HTTPStatus.OK:
                text = chunk.output.choices[0].message.content
                if (len(text) - last_len) <= delay_len:
                    in_delay = True
                    continue
                else:
                    in_delay = False
                    real_text = text[:-delay_len]
                    now_rsp = real_text[last_len:]
                    yield [Message(ASSISTANT, now_rsp)]
                    last_len = len(real_text)
            else:
                raise ModelServiceError(code=chunk.code, message=chunk.message)
        if text and (in_delay or (last_len != len(text))):
            yield [Message(ASSISTANT, text[last_len:])]

    @staticmethod
    def _full_stream_output(response) -> Iterator[List[Message]]:
        for chunk in response:
            if chunk.status_code == HTTPStatus.OK:
                yield [Message(ASSISTANT, chunk.output.choices[0].message.content)]
            else:
                raise ModelServiceError(code=chunk.code, message=chunk.message)


def initialize_dashscope(cfg: Optional[Dict] = None) -> None:
    cfg = cfg or {}

    api_key = cfg.get('api_key', '')
    base_http_api_url = cfg.get('base_http_api_url', None)
    base_websocket_api_url = cfg.get('base_websocket_api_url', None)

    if not api_key:
        api_key = os.getenv('DASHSCOPE_API_KEY', 'EMPTY')
    if not base_http_api_url:
        base_http_api_url = os.getenv('DASHSCOPE_HTTP_URL', None)
    if not base_websocket_api_url:
        base_websocket_api_url = os.getenv('DASHSCOPE_WEBSOCKET_URL', None)

    api_key = api_key.strip()
    dashscope.api_key = api_key
    if base_http_api_url is not None:
        dashscope.base_http_api_url = base_http_api_url.strip()
    if base_websocket_api_url is not None:
        dashscope.base_websocket_api_url = base_websocket_api_url.strip()
