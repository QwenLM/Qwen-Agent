import copy
from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Tuple, Union

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import (CONTENT, DEFAULT_SYSTEM_MESSAGE, ROLE,
                                   SYSTEM, USER)
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
            self.llm_config = llm
            self.llm = get_chat_model(self.llm_config)
        else:
            self.llm = llm

        self.function_list = []
        self.function_map = {}
        if function_list:
            for function_name in function_list:
                self._init_tool(function_name)

        self.system_message = system_message

    def run(self, messages: List[Dict], **kwargs) -> Iterator[List[Dict]]:
        assert messages[-1][ROLE] == USER, 'you must send the user message'
        messages = copy.deepcopy(messages)
        if 'lang' not in kwargs:
            if has_chinese_chars([messages[-1][CONTENT], kwargs]):
                kwargs['lang'] = 'zh'
            else:
                kwargs['lang'] = 'en'
        return self._run(messages, **kwargs)

    @abstractmethod
    def _run(self,
             messages: List[Dict],
             lang: str = 'en',
             **kwargs) -> Iterator[List[Dict]]:
        raise NotImplementedError

    def _call_llm(self,
                  messages: List[Dict],
                  functions: Optional[List[Dict]] = None,
                  stream: bool = True,
                  delta_stream: bool = False) -> Iterator[List[Dict]]:
        """
        for an agent, default to call llm using full stream interfaces
        """
        messages = copy.deepcopy(messages)
        if messages[0][ROLE] != SYSTEM:
            messages.insert(0, {ROLE: SYSTEM, CONTENT: self.system_message})
        elif isinstance(messages[0][CONTENT], str):
            messages[0][CONTENT] = self.system_message + messages[0][CONTENT]
        else:
            assert isinstance(messages[0][CONTENT], list)
            messages[0][CONTENT] = [{
                'text': self.system_message
            }] + messages[0][CONTENT]
        return self.llm.chat(messages=messages,
                             functions=functions,
                             stream=stream,
                             delta_stream=delta_stream)

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
        if tool not in self.function_list:
            self.function_list.append(tool)
            self.function_map[tool_name] = TOOL_REGISTRY[tool_name](tool_cfg)

    def _detect_tool(self, message: Union[str,
                                          dict]) -> Tuple[bool, str, str, str]:
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
        assert isinstance(message, dict)
        if 'function_call' in message and message['function_call']:
            func_call = message['function_call']
            func_name = func_call.get('name', '')
            func_args = func_call.get('arguments', '')
        text = message.get('content', '')

        return (func_name is not None), func_name, func_args, text
