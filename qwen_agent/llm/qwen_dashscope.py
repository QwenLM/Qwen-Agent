import os
from http import HTTPStatus
from typing import Dict, Iterator, List, Optional

import dashscope

from qwen_agent.llm.base import BaseChatModel
from qwen_agent.log import logger

from .schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE, ROLE, SYSTEM,
                     USER)


class QwenChatAtDS(BaseChatModel):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.model = self.cfg.get('model', 'qwen-max')
        dashscope.api_key = os.getenv('DASHSCOPE_API_KEY',
                                      default=self.cfg.get('api_key', ''))
        assert dashscope.api_key, 'DASHSCOPE_API_KEY is required.'

    def _chat_stream(
        self,
        messages: List[Dict],
        stop: Optional[List[str]] = None,
        delta_stream: bool = False,
    ) -> Iterator[List[Dict]]:
        stop = stop or []
        response = dashscope.Generation.call(
            self.model,
            messages=messages,  # noqa
            stop_words=[{
                'stop_str': word,
                'mode': 'exclude'
            } for word in stop],
            result_format='message',
            stream=True,
            **self.generate_cfg)
        if delta_stream:
            return self.delta_stream_output(response)
        else:
            return self.full_stream_output(response)

    def _chat_no_stream(
        self,
        messages: List[Dict],
        stop: Optional[List[str]] = None,
    ) -> Iterator[List[Dict]]:
        stop = stop or []
        response = dashscope.Generation.call(
            self.model,
            messages=messages,  # noqa
            result_format='message',
            stream=False,
            stop_words=[{
                'stop_str': word,
                'mode': 'exclude'
            } for word in stop],
            **self.generate_cfg)
        if response.status_code == HTTPStatus.OK:
            yield self.wrapper_text_to_message_list(
                response.output.choices[0].message.content)
        else:
            err = 'Error code: %s, error message: %s' % (
                response.code,
                response.message,
            )
            logger.error(err)
            if response.code == 'DataInspectionFailed':
                err += '\n【异常输出】: 数据检查失败。【错误信息】: 输入数据可能包含不适当的内容。'
            yield self.wrapper_text_to_message_list(f'{err}')

    def _text_completion_no_stream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
    ) -> Iterator[List[Dict]]:
        if prompt == '':
            yield self.wrapper_text_to_message_list('')
        stop = stop or []
        response = dashscope.Generation.call(
            self.model,
            prompt=prompt,  # noqa
            stop_words=[{
                'stop_str': word,
                'mode': 'exclude'
            } for word in stop],
            result_format='message',
            stream=False,
            use_raw_prompt=True,
            **self.generate_cfg)
        if response.status_code == HTTPStatus.OK:
            # with open('debug.json', 'w', encoding='utf-8') as writer:
            #     writer.write(json.dumps(response, ensure_ascii=False))
            yield self.wrapper_text_to_message_list(
                response.output.choices[0].message.content)
        else:
            err = 'Error code: %s, error message: %s' % (
                response.code,
                response.message,
            )
            logger.error(err)
            if response.code == 'DataInspectionFailed':
                err += '\n【异常输出】: 数据检查失败。【错误信息】: 输入数据可能包含不适当的内容。'
            yield self.wrapper_text_to_message_list(f'{err}')

    def _text_completion_stream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        delta_stream: bool = False,
    ) -> Iterator[List[Dict]]:

        stop = stop or []
        response = dashscope.Generation.call(
            self.model,
            prompt=prompt,  # noqa
            stop_words=[{
                'stop_str': word,
                'mode': 'exclude'
            } for word in stop],
            result_format='message',
            stream=True,
            use_raw_prompt=True,
            **self.generate_cfg)
        if delta_stream:
            return self.delta_stream_output(response)
        else:
            return self.full_stream_output(response)

    def build_text_completion_prompt(self, messages: List[Dict]) -> str:
        im_start = '<|im_start|>'
        im_end = '<|im_end|>'
        if messages[0][ROLE] == SYSTEM:
            sys = messages[0][CONTENT]
            prompt = f'{im_start}{SYSTEM}\n{sys}{im_end}'
        else:
            prompt = f'{im_start}{SYSTEM}\n{DEFAULT_SYSTEM_MESSAGE}{im_end}'
        if messages[-1][ROLE] != ASSISTANT:
            # add one empty reply for the last round of ASSISTANT
            messages.append({ROLE: ASSISTANT, CONTENT: ''})

        for message in messages:
            if message[ROLE] == USER:
                query = message[CONTENT].lstrip('\n').rstrip()
                prompt += f'\n{im_start}{USER}\n{query}{im_end}'
            elif message[ROLE] == ASSISTANT:
                response = message[CONTENT].lstrip('\n').rstrip()
                prompt += f'\n{im_start}{ASSISTANT}\n{response}{im_end}'

        prompt = prompt[:-len(f'{im_end}')]
        return prompt

    def delta_stream_output(self, response) -> Iterator[List[Dict]]:
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
                    yield self.wrapper_text_to_message_list(now_rsp)
                    last_len = len(real_text)
            else:
                err = '\nError code: %s. Error message: %s' % (trunk.code,
                                                               trunk.message)
                logger.error(err)
                # todo: Better error handling
                if trunk.code == 'DataInspectionFailed':
                    err += '\n【异常输出】: 数据检查失败。【错误信息】: 输入数据可能包含不适当的内容。'
                text = ''
                yield self.wrapper_text_to_message_list(f'{err}')
                break
        # with open('debug.json', 'w', encoding='utf-8') as writer:
        #     writer.write(json.dumps(trunk, ensure_ascii=False))
        if text and (in_delay or (last_len != len(text))):
            yield self.wrapper_text_to_message_list(text[last_len:])

    def full_stream_output(self, response) -> Iterator[List[Dict]]:
        for trunk in response:
            if trunk.status_code == HTTPStatus.OK:
                yield self.wrapper_text_to_message_list(
                    trunk.output.choices[0].message.content)
            else:
                err = '\nError code: %s. Error message: %s' % (trunk.code,
                                                               trunk.message)
                logger.error(err)
                if trunk.code == 'DataInspectionFailed':
                    err += '\n【异常输出】: 数据检查失败。【错误信息】: 输入数据可能包含不适当的内容。'
                yield self.wrapper_text_to_message_list(f'{err}')
                break
