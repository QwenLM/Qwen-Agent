import os
from http import HTTPStatus
from pprint import pformat
from typing import Dict, Iterator, List, Optional

import dashscope

from qwen_agent.llm.base import ModelServiceError, register_llm
from qwen_agent.llm.function_calling import BaseFnCallModel
from qwen_agent.llm.text_base import format_as_text_messages
from qwen_agent.log import logger

from .schema import ContentItem, Message


@register_llm('qwenvl_dashscope')
class QwenVLChatAtDS(BaseFnCallModel):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.model = self.model or 'qwen-vl-max'

        cfg = cfg or {}
        api_key = cfg.get('api_key', '')
        if not api_key:
            api_key = os.getenv('DASHSCOPE_API_KEY', 'EMPTY')
        api_key = api_key.strip()
        dashscope.api_key = api_key

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool = False,
    ) -> Iterator[List[Message]]:
        if delta_stream:
            raise NotImplementedError

        messages = [msg.model_dump() for msg in messages]
        logger.debug(f'*{pformat(messages, indent=2)}*')
        response = dashscope.MultiModalConversation.call(
            model=self.model,
            messages=messages,
            result_format='message',
            stream=True,
            **self.generate_cfg)

        for trunk in response:
            if trunk.status_code == HTTPStatus.OK:
                yield _extract_vl_response(trunk)
            else:
                raise ModelServiceError(code=trunk.code, message=trunk.message)

    def _chat_no_stream(
        self,
        messages: List[Message],
    ) -> List[Message]:
        messages = [msg.model_dump() for msg in messages]
        logger.debug(f'*{pformat(messages, indent=2)}*')
        response = dashscope.MultiModalConversation.call(
            model=self.model,
            messages=messages,
            result_format='message',
            stream=False,
            **self.generate_cfg)
        if response.status_code == HTTPStatus.OK:
            return _extract_vl_response(response=response)
        else:
            raise ModelServiceError(code=response.code,
                                    message=response.message)

    def _postprocess_messages(self, messages: List[Message],
                              fncall_mode: bool) -> List[Message]:
        messages = super()._postprocess_messages(messages,
                                                 fncall_mode=fncall_mode)
        # Make VL return the same format as text models for easy usage
        messages = format_as_text_messages(messages)
        return messages


def _extract_vl_response(response) -> List[Message]:
    output = response.output.choices[0].message
    text_content = []
    for item in output.content:
        for k, v in item.items():
            if k in ('text', 'box'):
                text_content.append(ContentItem(text=v))
    return [Message(role=output.role, content=text_content)]
