# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import logging
import os
from pprint import pformat
from typing import Any, Dict, Iterator, List, Optional

import openai

from qwen_agent.utils.utils import format_as_text_message

if openai.__version__.startswith('0.'):
    from openai.error import OpenAIError  # noqa
else:
    from openai import OpenAIError

from qwen_agent.llm.base import ModelServiceError, register_llm
from qwen_agent.llm.function_calling import BaseFnCallModel
from qwen_agent.llm.schema import ASSISTANT, FunctionCall, Message
from qwen_agent.log import logger


def _safe_model_dump(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if hasattr(value, 'model_dump'):
        return value.model_dump(exclude_none=True)
    if hasattr(value, 'dict'):
        return value.dict()
    if hasattr(value, 'to_dict_recursive'):
        return value.to_dict_recursive()
    if hasattr(value, 'to_dict'):
        return value.to_dict()
    if hasattr(value, '__dict__'):
        return {k: v for k, v in value.__dict__.items() if (not k.startswith('_')) and (v is not None)}
    return value


def _usage_extra(response: Any) -> Optional[dict]:
    if isinstance(response, dict):
        usage = response.get('usage')
    else:
        usage = getattr(response, 'usage', None)
    if usage is None:
        return None
    return {'usage': _safe_model_dump(usage)}


def _merge_extra(extra: Optional[dict], usage_extra: Optional[dict]) -> Optional[dict]:
    if not usage_extra:
        return extra
    merged_extra = copy.deepcopy(extra) if extra else {}
    merged_extra.update(usage_extra)
    return merged_extra


@register_llm('oai')
class TextChatAtOAI(BaseFnCallModel):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.model = self.model or 'gpt-4o-mini'
        cfg = cfg or {}

        api_base = cfg.get('api_base')
        api_base = api_base or cfg.get('base_url')
        api_base = api_base or cfg.get('model_server')
        api_base = (api_base or '').strip()

        api_key = cfg.get('api_key')
        api_key = api_key or os.getenv('OPENAI_API_KEY')
        api_key = (api_key or 'EMPTY').strip()

        if openai.__version__.startswith('0.'):
            if api_base:
                openai.api_base = api_base
            if api_key:
                openai.api_key = api_key
            self._complete_create = openai.Completion.create
            self._chat_complete_create = openai.ChatCompletion.create
        else:
            api_kwargs = {}
            if api_base:
                api_kwargs['base_url'] = api_base
            if api_key:
                api_kwargs['api_key'] = api_key

            def _chat_complete_create(*args, **kwargs):
                # OpenAI API v1 does not allow the following args, must pass by extra_body
                extra_params = ['top_k', 'repetition_penalty']
                if any((k in kwargs) for k in extra_params):
                    kwargs['extra_body'] = copy.deepcopy(kwargs.get('extra_body', {}))
                    for k in extra_params:
                        if k in kwargs:
                            kwargs['extra_body'][k] = kwargs.pop(k)
                if 'request_timeout' in kwargs:
                    kwargs['timeout'] = kwargs.pop('request_timeout')

                client = openai.OpenAI(**api_kwargs)
                return client.chat.completions.create(*args, **kwargs)

            def _complete_create(*args, **kwargs):
                # OpenAI API v1 does not allow the following args, must pass by extra_body
                extra_params = ['top_k', 'repetition_penalty']
                if any((k in kwargs) for k in extra_params):
                    kwargs['extra_body'] = copy.deepcopy(kwargs.get('extra_body', {}))
                    for k in extra_params:
                        if k in kwargs:
                            kwargs['extra_body'][k] = kwargs.pop(k)
                if 'request_timeout' in kwargs:
                    kwargs['timeout'] = kwargs.pop('request_timeout')

                client = openai.OpenAI(**api_kwargs)
                return client.completions.create(*args, **kwargs)

            self._complete_create = _complete_create
            self._chat_complete_create = _chat_complete_create

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool,
        generate_cfg: dict,
    ) -> Iterator[List[Message]]:
        messages = self.convert_messages_to_dicts(messages)
        logger.debug(f'LLM Input generate_cfg: \n{generate_cfg}')
        try:
            response = self._chat_complete_create(model=self.model, messages=messages, stream=True, **generate_cfg)
            if delta_stream:
                for chunk in response:
                    usage_extra = _usage_extra(chunk)
                    has_output = False
                    if chunk.choices:
                        if hasattr(chunk.choices[0].delta,
                                   'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                            has_output = True
                            yield [
                                Message(role=ASSISTANT,
                                        content='',
                                        reasoning_content=chunk.choices[0].delta.reasoning_content,
                                        extra=usage_extra)
                            ]
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                            has_output = True
                            yield [Message(role=ASSISTANT, content=chunk.choices[0].delta.content, extra=usage_extra)]
                    if usage_extra and not has_output:
                        yield [Message(role=ASSISTANT, content='', extra=usage_extra)]
            else:
                full_response = ''
                full_reasoning_content = ''
                full_tool_calls = []

                def _build_full_response(usage_extra: Optional[dict] = None) -> List[Message]:
                    res = []
                    if full_reasoning_content:
                        res.append(
                            Message(role=ASSISTANT,
                                    content='',
                                    reasoning_content=full_reasoning_content,
                                    extra=usage_extra))
                    if full_response:
                        res.append(Message(role=ASSISTANT, content=full_response, extra=usage_extra))
                    if full_tool_calls:
                        tool_calls = copy.deepcopy(full_tool_calls) if usage_extra else full_tool_calls
                        if usage_extra:
                            for tool_call in tool_calls:
                                tool_call.extra = _merge_extra(tool_call.extra, usage_extra)
                        res += tool_calls
                    return res

                for chunk in response:
                    usage_extra = _usage_extra(chunk)
                    if chunk.choices:
                        if hasattr(chunk.choices[0].delta,
                                   'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                            full_reasoning_content += chunk.choices[0].delta.reasoning_content
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                        if hasattr(chunk.choices[0].delta, 'tool_calls') and chunk.choices[0].delta.tool_calls:
                            for tc in chunk.choices[0].delta.tool_calls:
                                if full_tool_calls and (not tc.id or
                                                        tc.id == full_tool_calls[-1]['extra']['function_id']):
                                    if tc.function.name:
                                        full_tool_calls[-1].function_call['name'] += tc.function.name
                                    if tc.function.arguments:
                                        full_tool_calls[-1].function_call['arguments'] += tc.function.arguments
                                else:
                                    full_tool_calls.append(
                                        Message(role=ASSISTANT,
                                                content='',
                                                function_call=FunctionCall(name=tc.function.name,
                                                                           arguments=tc.function.arguments),
                                                extra={'function_id': tc.id}))

                        yield _build_full_response(usage_extra)
                    elif usage_extra:
                        res = _build_full_response(usage_extra)
                        if res:
                            yield res
        except OpenAIError as ex:
            raise ModelServiceError(exception=ex)

    def _chat_no_stream(
        self,
        messages: List[Message],
        generate_cfg: dict,
    ) -> List[Message]:
        messages = self.convert_messages_to_dicts(messages)
        try:
            response = self._chat_complete_create(model=self.model, messages=messages, stream=False, **generate_cfg)
            usage_extra = _usage_extra(response)
            if hasattr(response.choices[0].message, 'reasoning_content'):
                return [
                    Message(role=ASSISTANT,
                            content=response.choices[0].message.content,
                            reasoning_content=response.choices[0].message.reasoning_content,
                            extra=usage_extra)
                ]
            else:
                return [Message(role=ASSISTANT, content=response.choices[0].message.content, extra=usage_extra)]
        except OpenAIError as ex:
            raise ModelServiceError(exception=ex)

    def convert_messages_to_dicts(self, messages: List[Message]) -> List[dict]:
        # TODO: Change when the VLLM deployed model needs to pass reasoning_complete.
        #  At this time, in order to be compatible with lower versions of vLLM,
        #  and reasoning content is currently not useful
        messages = [format_as_text_message(msg, add_upload_info=False) for msg in messages]
        messages = [msg.model_dump() for msg in messages]
        messages = self._conv_qwen_agent_messages_to_oai(messages)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'LLM Input: \n{pformat(messages, indent=2)}')
        return messages
