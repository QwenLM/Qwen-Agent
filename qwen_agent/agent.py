from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.llm import get_chat_model
from qwen_agent.llm.base import BaseChatModel
from qwen_agent.tools import TOOL_REGISTRY
from qwen_agent.utils.utils import has_chinese_chars


class Agent(ABC):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_instruction: Optional[str] = None,
                 storage_path: Optional[str] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 **kwargs):
        """
        init tools/llm for one agent

        :param function_list: Optional[List[Union[str, Dict]]] :
            (1)When str: tool names
            (2)When Dict: tool cfg
        :param llm: Optional[Union[Dict, BaseChatModel]]:
            (1) When Dict: set the config of llm as {'model': '', 'api_key': '', 'model_server': ''}
            (2) When BaseChatModel: llm is sent by another agent
        :param storage_path: If not specified otherwise, all data will be stored here in KV pairs by memory
        :param name: the name of agent
        :param description: the description of agent, which is used for multi_agent
        :param kwargs: other potential parameters
        """
        if isinstance(llm, Dict):
            self.llm_config = llm
            self.llm = get_chat_model(**self.llm_config)
        else:
            self.llm = llm
        self.stream = True

        self.function_list = []
        self.function_map = {}
        if function_list:
            for function_name in function_list:
                self._register_tool(function_name)

        self.storage_path = storage_path
        self.mem = None
        self.name = name
        self.description = description
        self.system_instruction = system_instruction or 'You are a helpful assistant.'

    def run(self, *args, **kwargs) -> Union[str, Iterator[str]]:
        if 'lang' not in kwargs:
            if has_chinese_chars([args, kwargs]):
                kwargs['lang'] = 'zh'
            else:
                kwargs['lang'] = 'en'
        return self._run(*args, **kwargs)

    @abstractmethod
    def _run(self, *args, **kwargs) -> Union[str, Iterator[str]]:
        raise NotImplementedError

    def _call_llm(
        self,
        prompt: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        stop: Optional[List[str]] = None,
    ) -> Union[str, Iterator[str]]:
        return self.llm.chat(
            prompt=prompt,
            messages=messages,
            stop=stop,
            stream=self.stream,
        )

    def _call_tool(self, tool_name: str, tool_args: str, **kwargs):
        """
        Use when calling tools in bot()

        """
        return self.function_map[tool_name].call(tool_args, **kwargs)

    def _register_tool(self, tool: Union[str, Dict]):
        """
        Instantiate the global tool for the agent

        """
        tool_name = tool
        tool_cfg = None
        if isinstance(tool, Dict):
            tool_name = tool['name']
            tool_cfg = tool
        if tool_name not in TOOL_REGISTRY:
            raise NotImplementedError
        if tool not in self.function_list:
            self.function_list.append(tool)
            self.function_map[tool_name] = TOOL_REGISTRY[tool_name](tool_cfg)

    def _detect_tool(self, message: Union[str, dict]):
        # use built-in default judgment functions
        if isinstance(message, str):
            return self._detect_tool_by_special_token(message)
        else:
            return self._detect_tool_by_func_call(message)

    def _detect_tool_by_special_token(self, text: str):
        """
        A built-in tool call detection: After encapsulating function calls in the LLM layer, this is no longer needed

        """
        special_func_token = '\nAction:'
        special_args_token = '\nAction Input:'
        special_obs_token = '\nObservation:'
        func_name, func_args = None, None
        i = text.rfind(special_func_token)
        j = text.rfind(special_args_token)
        k = text.rfind(special_obs_token)
        if 0 <= i < j:  # If the text has `Action` and `Action input`,
            if k < j:  # but does not contain `Observation`,
                # then it is likely that `Observation` is ommited by the LLM,
                # because the output text may have discarded the stop word.
                text = text.rstrip() + special_obs_token  # Add it back.
            k = text.rfind(special_obs_token)
            func_name = text[i + len(special_func_token):j].strip()
            func_args = text[j + len(special_args_token):k].strip()
            text = text[:k]  # Discard '\nObservation:'.

        return (func_name is not None), func_name, func_args, text

    def _detect_tool_by_func_call(self, message: Dict):
        """
        A built-in tool call detection for func_call format

        """
        func_name = None
        func_args = None
        if 'function_call' in message and message['function_call']:
            func_call = message['function_call']
            func_name = func_call.get('name', '')
            func_args = func_call.get('arguments', '')
        text = message['content']

        return (func_name is not None), func_name, func_args, text

    def send(self,
             message: Union[Dict, str],
             recipient: 'Agent',
             request_reply: Optional[bool] = None,
             **kwargs):
        recipient.receive(message, self, request_reply)

    def receive(self,
                message: Union[Dict, str],
                sender: 'Agent',
                request_reply: Optional[bool] = None,
                **kwargs):
        if request_reply is False or request_reply is None:
            return
        reply = self.run(message, sender=sender, **kwargs)
        if reply is not None:
            self.send(reply, sender, **kwargs)
