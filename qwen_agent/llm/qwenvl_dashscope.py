import os
from http import HTTPStatus
from typing import Dict, Iterator, List, Optional

import dashscope

from qwen_agent.llm.base import BaseChatModel, ModelServiceError, register_llm

from .schema import CONTENT, Message


@register_llm('qwenvl_dashscope')
class QwenVLChatAtDS(BaseChatModel):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)

        self.model = self.cfg.get('model', 'qwen-vl-max')
        api_key = self.cfg.get('api_key', '')
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
        response = dashscope.MultiModalConversation.call(
            model=self.model,
            messages=messages,
            result_format='message',
            stream=True,
            **self.generate_cfg)

        for trunk in response:
            if trunk.status_code == HTTPStatus.OK:
                output = trunk.output.choices[0].message
                new_content = []
                for item in output[CONTENT]:
                    for k, v in item.items():
                        if k == 'box':
                            new_content.append({'text': v})
                        elif k == 'result_image':
                            continue
                        else:
                            new_content.append({k: v})
                output[CONTENT] = new_content
                yield [Message(**output)]
            else:
                err = '\nError code: %s. Error message: %s' % (trunk.code,
                                                               trunk.message)
                raise ModelServiceError(err)

    def _chat_no_stream(
        self,
        messages: List[Message],
    ) -> List[Message]:
        messages = [msg.model_dump() for msg in messages]
        response = dashscope.MultiModalConversation.call(
            model=self.model,
            messages=messages,
            result_format='message',
            stream=False,
            **self.generate_cfg)
        if response.status_code == HTTPStatus.OK:
            output = response.output.choices[0].message
            new_content = []
            for item in output[CONTENT]:
                for k, v in item.items():
                    if k == 'box':
                        new_content.append({'text': v})
                    elif k == 'result_image':
                        continue
                    else:
                        new_content.append({k: v})
            output[CONTENT] = new_content
            return [Message(**output)]
        else:
            err = 'Error code: %s, error message: %s' % (
                response.code,
                response.message,
            )
            raise ModelServiceError(err)
