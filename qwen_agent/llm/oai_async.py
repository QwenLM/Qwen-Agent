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
from typing import Dict, List, Optional, Union

import openai
from openai import AsyncOpenAI, DefaultAsyncHttpxClient

from qwen_agent.utils.utils import format_as_text_message

if openai.__version__.startswith('0.'):
    raise RuntimeError("oai_async requires openai>=1.0.0")
else:
    from openai import OpenAIError

from qwen_agent.llm.base import ModelServiceError, register_llm
from qwen_agent.llm.function_calling import BaseFnCallModel
from qwen_agent.llm.schema import ASSISTANT, Message
from qwen_agent.log import logger


@register_llm('oai_async')
class TextChatAtOAIAsync(BaseFnCallModel):
    """Fully async version of TextChatAtOAI using openai.AsyncOpenAI."""

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

        self.api_kwargs = {}
        if api_base:
            self.api_kwargs['base_url'] = api_base
        if api_key:
            self.api_kwargs['api_key'] = api_key

        # Use DefaultAsyncHttpxClient for better async performance
        self.api_kwargs['http_client'] = DefaultAsyncHttpxClient()

        # Create AsyncOpenAI client
        self.client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        """Get or create AsyncOpenAI client."""
        if self.client is None:
            self.client = AsyncOpenAI(**self.api_kwargs)
        return self.client

    async def close(self):
        """Close the AsyncOpenAI client."""
        if self.client:
            await self.client.close()
            self.client = None

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool,
        generate_cfg: dict,
    ):
        """Stream not supported in async version, raise error."""
        raise NotImplementedError(
            "Streaming is not supported in TextChatAtOAIAsync. "
            "Please use stream=False or use the sync TextChatAtOAI class."
        )

    async def _chat_no_stream(
        self,
        messages: List[Message],
        generate_cfg: dict,
    ) -> List[Message]:
        """Async non-streaming chat completion using AsyncOpenAI."""
        messages = self.convert_messages_to_dicts(messages)
        try:
            # Handle extra parameters that need to go into extra_body
            generate_cfg = copy.deepcopy(generate_cfg)

            # Remove parameters that are not accepted by OpenAI API
            params_to_remove = ['lang', 'incremental_output']
            for param in params_to_remove:
                generate_cfg.pop(param, None)

            # Move some parameters to extra_body
            extra_params = ['top_k', 'repetition_penalty']
            if any((k in generate_cfg) for k in extra_params):
                generate_cfg['extra_body'] = copy.deepcopy(generate_cfg.get('extra_body', {}))
                for k in extra_params:
                    if k in generate_cfg:
                        generate_cfg['extra_body'][k] = generate_cfg.pop(k)
            if 'request_timeout' in generate_cfg:
                generate_cfg['timeout'] = generate_cfg.pop('request_timeout')

            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                **generate_cfg
            )

            if hasattr(response.choices[0].message, 'reasoning_content'):
                return [
                    Message(
                        role=ASSISTANT,
                        content=response.choices[0].message.content,
                        reasoning_content=response.choices[0].message.reasoning_content
                    )
                ]
            else:
                return [
                    Message(
                        role=ASSISTANT,
                        content=response.choices[0].message.content
                    )
                ]
        except OpenAIError as ex:
            raise ModelServiceError(exception=ex)

    def convert_messages_to_dicts(self, messages: List[Message]) -> List[dict]:
        """Convert messages to dict format for OpenAI API."""
        # TODO: Change when the VLLM deployed model needs to pass reasoning_complete.
        #  At this time, in order to be compatible with lower versions of vLLM,
        #  and reasoning content is currently not useful
        messages = [format_as_text_message(msg, add_upload_info=False) for msg in messages]
        messages = [msg.model_dump() for msg in messages]
        messages = self._conv_qwen_agent_messages_to_oai(messages)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'LLM Input: \n{pformat(messages, indent=2)}')
        return messages

    async def __aenter__(self):
        """Async context manager entry."""
        self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def chat(
        self,
        messages: List[Union['Message', Dict]],
        functions: Optional[List[Dict]] = None,
        stream: bool = False,
        delta_stream: bool = False,
        extra_generate_cfg: Optional[Dict] = None,
    ) -> Union[List['Message'], List[Dict]]:
        """Async LLM chat interface (non-streaming only).

        This is the async version of BaseChatModel.chat() that includes all
        preprocessing, postprocessing, and error handling logic.
        """
        import copy
        import random
        import asyncio
        import json
        from typing import Literal
        from pprint import pformat
        from qwen_agent.llm.schema import DEFAULT_SYSTEM_MESSAGE, SYSTEM, ASSISTANT, Message
        from qwen_agent.utils.utils import (
            has_chinese_messages, merge_generate_cfgs, format_as_text_message,
            json_dumps_compact
        )
        from qwen_agent.settings import DEFAULT_MAX_INPUT_TOKENS
        from qwen_agent.llm.base import (
            _truncate_input_messages_roughly, _format_as_text_messages,
            ModelServiceError
        )

        if stream:
            raise NotImplementedError("Streaming not supported in async version")

        # Unify the input messages to type List[Message]:
        messages = copy.deepcopy(messages)
        _return_message_type = 'dict'
        new_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                new_messages.append(Message(**msg))
            else:
                new_messages.append(msg)
                _return_message_type = 'message'
        messages = new_messages

        if not messages:
            raise ValueError('Messages can not be empty.')

        # Cache lookup (same as base.py:156-167)
        if self.cache is not None:
            cache_key = dict(messages=messages, functions=functions, extra_generate_cfg=extra_generate_cfg)
            cache_key: str = json_dumps_compact(cache_key, sort_keys=True)
            cache_value: str = self.cache.get(cache_key)
            if cache_value:
                cache_value: List[dict] = json.loads(cache_value)
                if _return_message_type == 'message':
                    cache_value: List[Message] = [Message(**m) for m in cache_value]
                return cache_value

        # Generate config (same as base.py:176-184)
        generate_cfg = merge_generate_cfgs(base_generate_cfg=self.generate_cfg, new_generate_cfg=extra_generate_cfg)
        if 'seed' not in generate_cfg:
            generate_cfg['seed'] = random.randint(a=0, b=2**30)
        if 'lang' in generate_cfg:
            lang: Literal['en', 'zh'] = generate_cfg.pop('lang')
        else:
            lang: Literal['en', 'zh'] = 'zh' if has_chinese_messages(messages) else 'en'
        if not stream and 'incremental_output' in generate_cfg:
            generate_cfg.pop('incremental_output')

        # Add system message (same as base.py:186-187)
        if DEFAULT_SYSTEM_MESSAGE and messages[0].role != SYSTEM:
            messages = [Message(role=SYSTEM, content=DEFAULT_SYSTEM_MESSAGE)] + messages

        # Token truncation (same as base.py:189-195)
        max_input_tokens = generate_cfg.pop('max_input_tokens', DEFAULT_MAX_INPUT_TOKENS)
        if max_input_tokens > 0:
            messages = _truncate_input_messages_roughly(
                messages=messages,
                max_tokens=max_input_tokens,
            )

        # Function calling setup (same as base.py:197-209)
        if functions:
            fncall_mode = True
        else:
            fncall_mode = False
        if 'function_choice' in generate_cfg:
            fn_choice = generate_cfg['function_choice']
            valid_fn_choices = [f.get('name', f.get('name_for_model', None)) for f in (functions or [])]
            valid_fn_choices = ['auto', 'none'] + [f for f in valid_fn_choices if f]
            if fn_choice not in valid_fn_choices:
                raise ValueError(f'The value of function_choice must be one of the following: {valid_fn_choices}. '
                                 f'But function_choice="{fn_choice}" is received.')
            if fn_choice == 'none':
                fncall_mode = False

        # Preprocess messages (same as base.py:212-218)
        messages = self._preprocess_messages(messages,
                                             lang=lang,
                                             generate_cfg=generate_cfg,
                                             functions=functions,
                                             use_raw_api=self.use_raw_api)
        if not self.support_multimodal_input:
            messages = [format_as_text_message(msg, add_upload_info=False) for msg in messages]

        # use_raw_api check (same as base.py:220-223)
        if self.use_raw_api:
            raise NotImplementedError("use_raw_api not supported in async version")

        # Remove function-related keys if not in fncall mode (same as base.py:225-228)
        if not fncall_mode:
            for k in ['parallel_function_calls', 'function_choice', 'thought_in_content']:
                if k in generate_cfg:
                    del generate_cfg[k]

        # Call model service with retry (same as base.py:230-260)
        async def _call_model_service():
            if fncall_mode:
                # Call _chat_with_functions (need to implement async version)
                return await self._async_chat_with_functions(
                    messages=messages,
                    functions=functions,
                    generate_cfg=generate_cfg,
                    lang=lang,
                )
            else:
                # Handle continuation mode (same as base.py:242-244)
                if messages[-1].role == ASSISTANT:
                    raise NotImplementedError("Continuation mode not supported in async version")
                else:
                    return await self._async_chat(messages, generate_cfg=generate_cfg)

        # Retry logic (same as base.py:260)
        max_retries = self.max_retries
        num_retries = 0
        delay = 1.0

        while True:
            try:
                output = await _call_model_service()
                break
            except Exception as e:
                if not isinstance(e, ModelServiceError):
                    raise
                if max_retries <= 0 or num_retries >= max_retries:
                    raise
                if hasattr(e, 'code') and e.code == '400':
                    raise

                num_retries += 1
                jitter = 1.0 + random.random()
                delay = min(delay * 2.0, 300.0) * jitter
                logger.warning(f'ModelServiceError - {str(e).strip()} - Retry {num_retries}/{max_retries}')
                await asyncio.sleep(delay)

        # Postprocess (same as base.py:262-270)
        assert isinstance(output, list)
        logger.debug(f'LLM Output: \n{pformat([_.model_dump() for _ in output], indent=2)}')
        output = self._postprocess_messages(output, fncall_mode=fncall_mode, generate_cfg=generate_cfg)
        if not self.support_multimodal_output:
            output = _format_as_text_messages(messages=output)
        if self.cache:
            self.cache.set(cache_key, json_dumps_compact(output))
        return self._convert_messages_to_target_type(output, _return_message_type)

    async def _async_chat(self, messages, generate_cfg: dict):
        """Async version of _chat (non-streaming only)"""
        return await self._chat_no_stream(messages=messages, generate_cfg=generate_cfg)

    async def _async_chat_with_functions(self, messages, functions, generate_cfg, lang):
        """Async version of BaseFnCallModel._chat_with_functions (function_calling.py:120-136)"""
        # Same logic as function_calling.py:132-136
        generate_cfg = copy.deepcopy(generate_cfg)
        for k in ['parallel_function_calls', 'function_choice', 'thought_in_content']:
            if k in generate_cfg:
                del generate_cfg[k]
        return await self._async_continue_assistant_response(messages, generate_cfg=generate_cfg)

    async def _async_continue_assistant_response(self, messages, generate_cfg):
        """Async version of BaseChatModel._continue_assistant_response (base.py:316-323)"""
        from qwen_agent.llm.function_calling import simulate_response_completion_with_chat
        messages = simulate_response_completion_with_chat(messages)
        return await self._async_chat(messages, generate_cfg=generate_cfg)
