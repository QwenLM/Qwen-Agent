import copy
from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Tuple, Union

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import (CONTENT, DEFAULT_SYSTEM_MESSAGE, ROLE,
                                   SYSTEM, USER, ContentItem, Message)
from qwen_agent.tools import TOOL_REGISTRY
from qwen_agent.utils.utils import has_chinese_chars


class Agent(ABC):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 **kwargs):
        """
        init tools/llm for one agent

        :param function_list: Optional[List[Union[str, Dict]]] :
            (1)When str: tool names
            (2)When Dict: tool cfg
        :param llm: Optional[Union[Dict, BaseChatModel]]:
            (1) When Dict: set the config of llm as {'model': '', 'api_key': '', 'model_server': ''}
            (2) When BaseChatModel: llm is sent by another agent
        :param system_message: If not specified during the conversation, using this default system message for llm chat
        :param name: the name of agent
        :param description: the description of agent, which is used for multi_agent
        :param kwargs: other potential parameters
        """
        if isinstance(llm, dict):
            self.llm = get_chat_model(llm)
        else:
            self.llm = llm

        self.function_map = {}
        if function_list:
            for tool in function_list:
                self._init_tool(tool)

        self.system_message = system_message

    def run(self, messages: List[Union[Dict, Message]],
            **kwargs) -> Union[Iterator[List[Message]], Iterator[List[Dict]]]:
        assert messages[-1][ROLE] == USER, 'you must send the user message'
        messages = copy.deepcopy(messages)
        _return_message_type = 'dict'
        new_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                new_messages.append(Message(**msg))
            else:
                new_messages.append(msg)
                _return_message_type = 'message'

        if 'lang' not in kwargs:
            if has_chinese_chars([new_messages[-1][CONTENT], kwargs]):
                kwargs['lang'] = 'zh'
            else:
                kwargs['lang'] = 'en'

        for rsp in self._run(messages=new_messages, **kwargs):
            if _return_message_type == 'message':
                yield [Message(**x) if isinstance(x, dict) else x for x in rsp]
            else:
                yield [
                    x.model_dump() if not isinstance(x, dict) else x
                    for x in rsp
                ]

    @abstractmethod
    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             **kwargs) -> Iterator[List[Message]]:
        raise NotImplementedError

    def _call_llm(
        self,
        messages: List[Message],
        functions: Optional[List[Dict]] = None,
        stream: bool = True,
    ) -> Iterator[List[Message]]:
        """
        for an agent, default to call llm using full stream interfaces
        """
        messages = copy.deepcopy(messages)
        if messages[0][ROLE] != SYSTEM:
            messages.insert(0, Message(role=SYSTEM,
                                       content=self.system_message))
        elif isinstance(messages[0][CONTENT], str):
            messages[0][CONTENT] = self.system_message + messages[0][CONTENT]
        else:
            assert isinstance(messages[0][CONTENT], list)
            messages[0][CONTENT] = [ContentItem(text=self.system_message)
                                    ] + messages[0][CONTENT]
        return self.llm.chat(messages=messages,
                             functions=functions,
                             stream=stream)

    def _call_tool(self,
                   tool_name: str,
                   tool_args: Union[str, dict] = '{}',
                   **kwargs):
        """
        Use when calling tools in bot()

        """
        if tool_name not in self.function_map:
            raise ValueError(f'This agent cannot call tool {tool_name}.')
        return self.function_map[tool_name].call(tool_args, **kwargs)

    def _init_tool(self, tool: Union[str, Dict]):
        """
        Instantiate the global tool for the agent

        """
        tool_name = tool
        tool_cfg = None
        if isinstance(tool, dict):
            tool_name = tool['name']
            tool_cfg = tool
        if tool_name not in TOOL_REGISTRY:
            raise NotImplementedError
        if tool_name not in self.function_map:
            self.function_map[tool_name] = TOOL_REGISTRY[tool_name](tool_cfg)

    def _detect_tool(self, message: Message) -> Tuple[bool, str, str, str]:
        """
        A built-in tool call detection for func_call format
        :param message: one message
        :return:
            - bool: need to call tool or not
            - str: tool name
            - str: tool args
            - str: text replies except for tool calls
        """
        func_name = None
        func_args = None

        if message.function_call:
            func_call = message.function_call
            func_name = func_call.name
            func_args = func_call.arguments
        text = message.content
        if not text:
            text = ''

        return (func_name is not None), func_name, func_args, text
