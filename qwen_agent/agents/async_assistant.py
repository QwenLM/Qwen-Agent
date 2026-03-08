# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
# Async version of Qwen Agent framework - Non-streaming async implementation

import asyncio
import copy
import json
import traceback
from abc import ABC, abstractmethod
from typing import Dict, List, Literal, Optional, Tuple, Union

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE, FUNCTION,
                                   ROLE, SYSTEM, ContentItem, Message)
from qwen_agent.log import logger
from qwen_agent.memory import Memory
from qwen_agent.settings import MAX_LLM_CALL_PER_RUN
from qwen_agent.tools import TOOL_REGISTRY, BaseTool, MCPManager
from qwen_agent.tools.base import ToolServiceError
from qwen_agent.tools.simple_doc_parser import DocParserError
from qwen_agent.utils.utils import (extract_files_from_messages, has_chinese_messages)


class AsyncAgent(ABC):
    """Async base class for Agent - follows Qwen Agent's architecture"""

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[dict, object]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 **kwargs):
        """Initialize the async agent"""
        # Use Qwen Agent's get_chat_model to create LLM instance
        if isinstance(llm, dict):
            self.llm = get_chat_model(llm)
        else:
            self.llm = llm or get_chat_model()

        self.function_map = {}
        if function_list:
            for tool in function_list:
                self._init_tool(tool)

        self.system_message = system_message
        self.name = name
        self.description = description

    async def run(self, messages: List[Union[Dict, Message]], **kwargs) -> List[Union[Message, Dict]]:
        """Run the agent and return complete response (async)

        This follows the same logic as sync Agent.run(), just async
        """
        messages = copy.deepcopy(messages)
        _return_message_type = 'dict'
        new_messages = []

        # Convert to Message objects (same as sync version)
        if not messages:
            _return_message_type = 'message'
        for msg in messages:
            if isinstance(msg, dict):
                new_messages.append(Message(**msg))
            else:
                new_messages.append(msg)
                _return_message_type = 'message'

        # Detect language (same as sync version)
        if 'lang' not in kwargs:
            if has_chinese_messages(new_messages):
                kwargs['lang'] = 'zh'
            else:
                kwargs['lang'] = 'en'

        # Add system message (same as sync version)
        if self.system_message:
            if not new_messages or new_messages[0][ROLE] != SYSTEM:
                new_messages.insert(0, Message(role=SYSTEM, content=self.system_message))
            else:
                if isinstance(new_messages[0][CONTENT], str):
                    new_messages[0][CONTENT] = self.system_message + '\n\n' + new_messages[0][CONTENT]
                else:
                    assert isinstance(new_messages[0][CONTENT], list)
                    assert new_messages[0][CONTENT][0].text
                    new_messages[0][CONTENT] = [
                        ContentItem(text=self.system_message + '\n\n')
                    ] + new_messages[0][CONTENT]

        # Run agent logic (async version)
        response = await self._run(messages=new_messages, **kwargs)

        # Set agent name (same as sync version)
        for msg in response:
            if not msg.name and self.name:
                msg.name = self.name

        # Convert back to requested format (same as sync version)
        if _return_message_type == 'message':
            return [Message(**x) if isinstance(x, dict) else x for x in response]
        else:
            return [x.model_dump() if not isinstance(x, dict) else x for x in response]

    @abstractmethod
    async def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> List[Message]:
        """Agent logic implementation (must be async)"""
        raise NotImplementedError

    async def _call_llm(
        self,
        messages: List[Message],
        functions: Optional[List[Dict]] = None,
        extra_generate_cfg: Optional[dict] = None,
    ) -> List[Message]:
        """Async LLM call - supports both async and sync LLMs"""
        # Check if LLM has async chat method
        if hasattr(self.llm, 'chat') and asyncio.iscoroutinefunction(self.llm.chat):
            # True async LLM with async chat method (like TextChatAtOAIAsync)
            # This properly goes through all preprocessing, postprocessing, and retry logic
            result = await self.llm.chat(
                messages=messages,
                functions=functions,
                stream=False,
                extra_generate_cfg=extra_generate_cfg
            )
            return result
        else:
            # Fallback to sync LLM wrapped in executor
            loop = asyncio.get_event_loop()

            def _sync_chat():
                return list(self.llm.chat(
                    messages=messages,
                    functions=functions,
                    stream=False,
                    extra_generate_cfg=extra_generate_cfg
                ))

            result = await loop.run_in_executor(None, _sync_chat)
            return result

    async def _call_tool(
        self,
        tool_name: str,
        tool_args: Union[str, dict] = '{}',
        **kwargs
    ) -> Union[str, List[ContentItem]]:
        """Async tool calling (same logic as sync version)"""
        if tool_name not in self.function_map:
            return f'Tool {tool_name} does not exists.'

        tool = self.function_map[tool_name]
        try:
            # Check if tool.call is async
            if asyncio.iscoroutinefunction(tool.call):
                tool_result = await tool.call(tool_args, **kwargs)
            else:
                # Run synchronous call in thread pool
                loop = asyncio.get_event_loop()
                tool_result = await loop.run_in_executor(
                    None,
                    lambda: tool.call(tool_args, **kwargs)
                )
        except (ToolServiceError, DocParserError) as ex:
            raise ex
        except Exception as ex:
            exception_type = type(ex).__name__
            exception_message = str(ex)
            traceback_info = ''.join(traceback.format_tb(ex.__traceback__))
            error_message = (
                f'An error occurred when calling tool `{tool_name}`:\n'
                f'{exception_type}: {exception_message}\n'
                f'Traceback:\n{traceback_info}'
            )
            logger.warning(error_message)
            return error_message

        if isinstance(tool_result, str):
            return tool_result
        elif isinstance(tool_result, list) and all(isinstance(item, ContentItem) for item in tool_result):
            return tool_result
        else:
            return json.dumps(tool_result, ensure_ascii=False, indent=4)

    def _init_tool(self, tool: Union[str, Dict, BaseTool]):
        """Initialize a tool (same as sync version)"""
        if isinstance(tool, BaseTool):
            tool_name = tool.name
            if tool_name in self.function_map:
                logger.warning(f'Repeatedly adding tool {tool_name}, will use the newest tool')
            self.function_map[tool_name] = tool
        elif isinstance(tool, dict) and 'mcpServers' in tool:
            tools = MCPManager().initConfig(tool)
            for t in tools:
                tool_name = t.name
                if tool_name in self.function_map:
                    logger.warning(f'Repeatedly adding tool {tool_name}, will use the newest tool')
                self.function_map[tool_name] = t
        else:
            if isinstance(tool, dict):
                tool_name = tool['name']
                tool_cfg = tool
            else:
                tool_name = tool
                tool_cfg = None
            if tool_name not in TOOL_REGISTRY:
                raise ValueError(f'Tool {tool_name} is not registered.')

            if tool_name in self.function_map:
                logger.warning(f'Repeatedly adding tool {tool_name}, will use the newest tool')
            self.function_map[tool_name] = TOOL_REGISTRY[tool_name](tool_cfg)

    def _detect_tool(self, message: Message) -> Tuple[bool, str, str, str]:
        """Detect if message contains tool call (same as sync version)"""
        func_name = None
        func_args = None

        if message.function_call:
            func_call = message.function_call
            func_name = func_call.name
            func_args = func_call.arguments # TODO: update 

        text = message.content if message.content else ''
        return (func_name is not None), func_name, func_args, text


class AsyncFnCallAgent(AsyncAgent):
    """Async function call agent with tool use ability (follows sync FnCallAgent)"""

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, object]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 files: Optional[List[str]] = None,
                 **kwargs):
        super().__init__(
            function_list=function_list,
            llm=llm,
            system_message=system_message,
            name=name,
            description=description
        )

        if not hasattr(self, 'mem'):
            # Initialize memory for file management
            mem_llm_cfg = None
            if hasattr(self.llm, 'model'):
                if 'qwq' in self.llm.model.lower() or 'qvq' in self.llm.model.lower() or 'qwen3' in self.llm.model.lower():
                    mem_llm_cfg = {
                        'model': 'qwen-turbo',
                        'model_type': 'qwen_dashscope',
                        'generate_cfg': {'max_input_tokens': 30000}
                    }
            self.mem = Memory(llm=mem_llm_cfg, files=files, **kwargs)

    async def _run(self, messages: List[Message], lang: Literal['en', 'zh'] = 'en', **kwargs) -> List[Message]:
        """Async agent loop with tool calling (same logic as sync version)"""
        messages = copy.deepcopy(messages)
        num_llm_calls_available = MAX_LLM_CALL_PER_RUN
        response = []

        while num_llm_calls_available > 0:
            num_llm_calls_available -= 1

            extra_generate_cfg = {'lang': lang}
            if kwargs.get('seed') is not None:
                extra_generate_cfg['seed'] = kwargs['seed']

            # Call LLM
            output = await self._call_llm(
                messages=messages,
                functions=[func.function for func in self.function_map.values()],
                extra_generate_cfg=extra_generate_cfg
            )

            if output:
                response.extend(output)
                messages.extend(output)
                used_any_tool = False

                # Check for tool calls
                for out in output:
                    use_tool, tool_name, tool_args, _ = self._detect_tool(out)
                    if use_tool:
                        # Execute tool
                        tool_result = await self._call_tool(
                            tool_name, tool_args, messages=messages, **kwargs
                        )
                        fn_msg = Message(
                            role=FUNCTION,
                            name=tool_name,
                            content=tool_result,
                            extra={'function_id': out.extra.get('function_id', '1')}
                        )
                        messages.append(fn_msg)
                        response.append(fn_msg)
                        used_any_tool = True

                if not used_any_tool:
                    # No tools called, we're done
                    break
            else:
                break

        return response

    async def _call_tool(self, tool_name: str, tool_args: Union[str, dict] = '{}', **kwargs) -> str:
        """Async tool calling with file access support (same logic as sync version)"""
        if tool_name not in self.function_map:
            return f'Tool {tool_name} does not exists.'

        # Handle file access
        if self.function_map[tool_name].file_access:
            assert 'messages' in kwargs
            files = extract_files_from_messages(kwargs['messages'], include_images=True) + self.mem.system_files
            return await super()._call_tool(tool_name, tool_args, files=files, **kwargs)
        else:
            return await super()._call_tool(tool_name, tool_args, **kwargs)


class AsyncAssistant(AsyncFnCallAgent):
    """Async assistant with RAG and function calling (follows sync Assistant)"""

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, object]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 files: Optional[List[str]] = None,
                 rag_cfg: Optional[Dict] = None):
        super().__init__(
            function_list=function_list,
            llm=llm,
            system_message=system_message,
            name=name,
            description=description,
            files=files,
            rag_cfg=rag_cfg
        )

    async def _run(self,
                   messages: List[Message],
                   lang: Literal['en', 'zh'] = 'en',
                   knowledge: str = '',
                   **kwargs) -> List[Message]:
        """Async Q&A with RAG and tool use (same logic as sync version)"""
        new_messages = await self._prepend_knowledge_prompt(
            messages=messages, lang=lang, knowledge=knowledge, **kwargs
        )
        return await super()._run(messages=new_messages, lang=lang, **kwargs)

    async def _prepend_knowledge_prompt(self,
                                        messages: List[Message],
                                        lang: Literal['en', 'zh'] = 'en',
                                        knowledge: str = '',
                                        **kwargs) -> List[Message]:
        """Prepend knowledge from RAG (async version of sync method)"""
        from qwen_agent.agents.assistant import (KNOWLEDGE_SNIPPET, KNOWLEDGE_TEMPLATE,
                                                  format_knowledge_to_source_and_content)

        messages = copy.deepcopy(messages)

        if not knowledge:
            # Retrieval knowledge from files (sync operation, run in executor)
            loop = asyncio.get_event_loop()
            last = await loop.run_in_executor(
                None,
                lambda: list(self.mem.run(messages=messages, lang=lang, **kwargs))[-1]
            )
            knowledge = last[-1][CONTENT]

        logger.debug(f'Retrieved knowledge of type `{type(knowledge).__name__}`:\n{knowledge}')

        if knowledge:
            knowledge = format_knowledge_to_source_and_content(knowledge)
            logger.debug(f'Formatted knowledge into type `{type(knowledge).__name__}`:\n{knowledge}')
        else:
            knowledge = []

        snippets = []
        for k in knowledge:
            snippets.append(KNOWLEDGE_SNIPPET[lang].format(source=k['source'], content=k['content']))

        knowledge_prompt = ''
        if snippets:
            knowledge_prompt = KNOWLEDGE_TEMPLATE[lang].format(knowledge='\n\n'.join(snippets))

        if knowledge_prompt:
            if messages and messages[0][ROLE] == SYSTEM:
                if isinstance(messages[0][CONTENT], str):
                    messages[0][CONTENT] += '\n\n' + knowledge_prompt
                else:
                    assert isinstance(messages[0][CONTENT], list)
                    messages[0][CONTENT] += [ContentItem(text='\n\n' + knowledge_prompt)]
            else:
                messages = [Message(role=SYSTEM, content=knowledge_prompt)] + messages

        return messages
