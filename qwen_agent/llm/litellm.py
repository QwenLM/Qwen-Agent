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
"""LiteLLM provider — unified access to 100+ LLM providers via the LiteLLM AI gateway.

Route chat completions through ``litellm.completion()`` using prefixed model names
(e.g. ``anthropic/claude-3-5-sonnet-20241022``, ``gemini/gemini-1.5-pro``,
``bedrock/anthropic.claude-3-sonnet-20240229-v1:0``). See
https://docs.litellm.ai/docs/providers for the full provider list.
"""
import logging
from pprint import pformat
from typing import Dict, Iterator, List, Optional

from qwen_agent.llm.base import ModelServiceError, register_llm
from qwen_agent.llm.function_calling import BaseFnCallModel
from qwen_agent.llm.schema import ASSISTANT, FunctionCall, Message
from qwen_agent.log import logger
from qwen_agent.utils.utils import format_as_text_message


@register_llm('litellm')
class TextChatAtLiteLLM(BaseFnCallModel):
    """LiteLLM-backed provider.

    Configuration example::

        cfg = {
            'model': 'anthropic/claude-3-5-sonnet-20241022',  # LiteLLM-style prefix
            'model_type': 'litellm',
            'api_key': '<provider-api-key>',  # optional; env vars also work
        }
    """

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.model = self.model or 'openai/gpt-4o-mini'
        cfg = cfg or {}

        api_base = cfg.get('api_base') or cfg.get('base_url') or cfg.get('model_server')
        self._api_base = (api_base or '').strip() or None

        api_key = cfg.get('api_key')
        self._api_key = api_key.strip() if isinstance(api_key, str) and api_key.strip() else None

    def _call_kwargs(self, messages: List[dict], generate_cfg: dict, stream: bool) -> dict:
        kwargs = {
            'model': self.model,
            'messages': messages,
            'stream': stream,
            # Qwen-Agent's base class always injects `seed` into generate_cfg, and
            # fncall_prompts adds `stop=['<|im_end|>', ...]` in some paths. These
            # kwargs are fine for OpenAI/Azure but throw UnsupportedParamsError on
            # other backends (e.g. Claude via Vertex, reported in issue #574).
            # `drop_params=True` tells LiteLLM to silently drop per-provider-
            # unsupported kwargs instead of raising. This is what the user in
            # #574 manually enabled on their LiteLLM proxy.
            'drop_params': True,
        }
        if self._api_key:
            kwargs['api_key'] = self._api_key
        if self._api_base:
            kwargs['api_base'] = self._api_base
        kwargs.update(generate_cfg)
        # Qwen-Agent passes `request_timeout`; LiteLLM expects `timeout`.
        if 'request_timeout' in kwargs:
            kwargs['timeout'] = kwargs.pop('request_timeout')
        return kwargs

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool,
        generate_cfg: dict,
    ) -> Iterator[List[Message]]:
        import litellm
        from litellm.exceptions import APIError

        messages = self.convert_messages_to_dicts(messages)
        logger.debug(f'LLM Input generate_cfg: \n{generate_cfg}')
        try:
            response = litellm.completion(**self._call_kwargs(messages, generate_cfg, stream=True))
            if delta_stream:
                for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        yield [Message(role=ASSISTANT, content='', reasoning_content=delta.reasoning_content)]
                    if hasattr(delta, 'content') and delta.content:
                        yield [Message(role=ASSISTANT, content=delta.content)]
            else:
                full_response = ''
                full_reasoning_content = ''
                full_tool_calls: List[Message] = []
                for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        full_reasoning_content += delta.reasoning_content
                    if hasattr(delta, 'content') and delta.content:
                        full_response += delta.content
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        for tc in delta.tool_calls:
                            if full_tool_calls and (not tc.id or
                                                    tc.id == full_tool_calls[-1].extra.get('function_id')):
                                if tc.function.name:
                                    full_tool_calls[-1].function_call.name += tc.function.name
                                if tc.function.arguments:
                                    full_tool_calls[-1].function_call.arguments += tc.function.arguments
                            else:
                                full_tool_calls.append(
                                    Message(role=ASSISTANT,
                                            content='',
                                            function_call=FunctionCall(name=tc.function.name or '',
                                                                       arguments=tc.function.arguments or ''),
                                            extra={'function_id': tc.id}))

                    res: List[Message] = []
                    if full_reasoning_content:
                        res.append(Message(role=ASSISTANT, content='', reasoning_content=full_reasoning_content))
                    if full_response:
                        res.append(Message(role=ASSISTANT, content=full_response))
                    if full_tool_calls:
                        res += full_tool_calls
                    yield res
        except APIError as ex:
            raise ModelServiceError(exception=ex)

    def _chat_no_stream(
        self,
        messages: List[Message],
        generate_cfg: dict,
    ) -> List[Message]:
        import litellm
        from litellm.exceptions import APIError

        messages = self.convert_messages_to_dicts(messages)
        try:
            response = litellm.completion(**self._call_kwargs(messages, generate_cfg, stream=False))
            msg = response.choices[0].message
            content = getattr(msg, 'content', '') or ''
            reasoning = getattr(msg, 'reasoning_content', None)
            if reasoning:
                return [Message(role=ASSISTANT, content=content, reasoning_content=reasoning)]
            return [Message(role=ASSISTANT, content=content)]
        except APIError as ex:
            raise ModelServiceError(exception=ex)

    def convert_messages_to_dicts(self, messages: List[Message]) -> List[dict]:
        messages = [format_as_text_message(msg, add_upload_info=False) for msg in messages]
        messages = [msg.model_dump() for msg in messages]
        messages = self._conv_qwen_agent_messages_to_oai(messages)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'LLM Input: \n{pformat(messages, indent=2)}')
        return messages
