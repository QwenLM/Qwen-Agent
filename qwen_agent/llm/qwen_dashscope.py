import copy
import json
import os
from http import HTTPStatus
from typing import Dict, Iterator, List, Optional, Union

import dashscope

from qwen_agent.llm.base import ModelServiceError, register_llm
from qwen_agent.log import logger

from .schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE, ROLE, SYSTEM,
                     USER, Message)
from .text_base import BaseTextChatModel


@register_llm('qwen_dashscope')
class QwenChatAtDS(BaseTextChatModel):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)

        self.model = self.cfg.get('model', 'qwen-max')
        if 'api_key' in cfg and cfg['api_key'].strip():
            dashscope.api_key = cfg['api_key']
        else:
            dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool = False,
    ) -> Iterator[List[Message]]:
        messages = [msg.model_dump() for msg in messages]
        response = dashscope.Generation.call(
            self.model,
            messages=messages,  # noqa
            result_format='message',
            stream=True,
            **self.generate_cfg)
        if delta_stream:
            return self._delta_stream_output(response)
        else:
            return self._full_stream_output(response)

    def _chat_no_stream(
        self,
        messages: List[Message],
    ) -> List[Message]:
        messages = [msg.model_dump() for msg in messages]
        response = dashscope.Generation.call(
            self.model,
            messages=messages,  # noqa
            result_format='message',
            stream=False,
            **self.generate_cfg)
        if response.status_code == HTTPStatus.OK:
            return [
                Message(ASSISTANT, response.output.choices[0].message.content)
            ]
        else:
            err = 'Error code: %s, error message: %s' % (
                response.code,
                response.message,
            )
            raise ModelServiceError(err)

    def _text_completion(
        self,
        messages: List[Union[Message, Dict]],
        stream: bool = True,
        delta_stream: bool = False,
    ) -> Union[List[Message], Iterator[List[Message]]]:
        messages = copy.deepcopy(messages)
        messages = [
            Message(**msg) if isinstance(msg, dict) else msg
            for msg in messages
        ]
        prompt = self._build_text_completion_prompt(messages)
        logger.debug('==== Inputted prompt ===')
        logger.debug(prompt)
        if stream:
            return self._text_completion_stream(prompt, delta_stream)
        else:
            return self._text_completion_no_stream(prompt)

    def _text_completion_no_stream(
        self,
        prompt: str,
    ) -> List[Message]:
        logger.debug(prompt)
        response = dashscope.Generation.call(self.model,
                                             prompt=prompt,
                                             result_format='message',
                                             stream=False,
                                             use_raw_prompt=True,
                                             **self.generate_cfg)
        if response.status_code == HTTPStatus.OK:
            # with open('debug.json', 'w', encoding='utf-8') as writer:
            #     writer.write(json.dumps(response, ensure_ascii=False))
            return [
                Message(ASSISTANT, response.output.choices[0].message.content)
            ]
        else:
            err = 'Error code: %s, error message: %s' % (
                response.code,
                response.message,
            )
            raise ModelServiceError(err)

    def _text_completion_stream(
        self,
        prompt: str,
        delta_stream: bool = False,
    ) -> Iterator[List[Message]]:
        response = dashscope.Generation.call(
            self.model,
            prompt=prompt,  # noqa
            result_format='message',
            stream=True,
            use_raw_prompt=True,
            **self.generate_cfg)
        if delta_stream:
            return self._delta_stream_output(response)
        else:
            return self._full_stream_output(response)

    def _build_text_completion_prompt(self, messages: List[Message]) -> str:
        im_start = '<|im_start|>'
        im_end = '<|im_end|>'
        if messages[0][ROLE] == SYSTEM:
            sys = messages[0][CONTENT]
            assert isinstance(
                sys,
                str), 'text completion does not support vl format messages'
            prompt = f'{im_start}{SYSTEM}\n{sys}{im_end}'
        else:
            prompt = f'{im_start}{SYSTEM}\n{DEFAULT_SYSTEM_MESSAGE}{im_end}'
        if messages[-1][ROLE] != ASSISTANT:
            # add one empty reply for the last round of ASSISTANT
            messages.append(Message(ASSISTANT, ''))
        for message in messages:
            assert isinstance(
                message[CONTENT],
                str), 'text completion does not support vl format messages'
            if message[ROLE] == USER:
                query = message[CONTENT].lstrip('\n').rstrip()
                prompt += f'\n{im_start}{USER}\n{query}{im_end}'
            elif message[ROLE] == ASSISTANT:
                response = message[CONTENT].lstrip('\n').rstrip()
                prompt += f'\n{im_start}{ASSISTANT}\n{response}{im_end}'

        prompt = prompt[:-len(f'{im_end}')]
        return prompt

    def _delta_stream_output(self, response) -> Iterator[List[Message]]:
        last_len = 0
        delay_len = 5
        in_delay = False
        text = ''
        for trunk in response:
            if trunk.status_code == HTTPStatus.OK:
                text = trunk.output.choices[0].message.content
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
                err = '\nError code: %s. Error message: %s' % (trunk.code,
                                                               trunk.message)
                raise ModelServiceError(err)
        # with open('debug.json', 'w', encoding='utf-8') as writer:
        #     writer.write(json.dumps(trunk, ensure_ascii=False))
        if text and (in_delay or (last_len != len(text))):
            yield [Message(ASSISTANT, text[last_len:])]

    def _full_stream_output(self, response) -> Iterator[List[Message]]:
        for trunk in response:
            if trunk.status_code == HTTPStatus.OK:
                yield [
                    Message(ASSISTANT, trunk.output.choices[0].message.content)
                ]
            else:
                err = '\nError code: %s. Error message: %s' % (trunk.code,
                                                               trunk.message)
                raise ModelServiceError(err)
        with open('debug.json', 'w', encoding='utf-8') as writer:
            writer.write(json.dumps(trunk, ensure_ascii=False))
