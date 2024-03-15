from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union

import json5

from qwen_agent.utils.utils import logger

TOOL_REGISTRY = {}


def register_tool(name, allow_overwrite=False):

    def decorator(cls):
        if name in TOOL_REGISTRY:
            if allow_overwrite:
                logger.warning(
                    f'Tool `{name}` already exists! Overwriting with class {cls}.'
                )
            else:
                raise ValueError(
                    f'Tool `{name}` already exists! Please ensure that the tool name is unique.'
                )
        if cls.name and (cls.name != name):
            raise ValueError(
                f'{cls.__name__}.name="{cls.name}" conflicts with @register_tool(name="{name}").'
            )
        cls.name = name
        TOOL_REGISTRY[name] = cls

        return cls

    return decorator


class BaseTool(ABC):
    name: str = ''
    description: str = ''
    parameters: List[Dict] = []

    def __init__(self, cfg: Optional[Dict] = None):
        self.cfg = cfg or {}
        if not self.name:
            raise ValueError(
                f'You must set {self.__class__.__name__}.name, either by @register_tool(name=...) or explicitly setting {self.__class__.__name__}.name'
            )

        self.name_for_human = self.cfg.get('name_for_human', self.name)
        if not hasattr(self, 'args_format'):
            self.args_format = self.cfg.get('args_format', '此工具的输入应为JSON对象。')
        self.function = self._build_function()
        self.file_access = False

    @abstractmethod
    def call(self, params: Union[str, dict],
             **kwargs) -> Union[str, list, dict]:
        """The interface for calling tools.

        Each tool needs to implement this function, which is the workflow of the tool.

        Args:
            params: The parameters of func_call.
            kwargs: Additional parameters for calling tools.

        Returns:
            The result returned by the tool, implemented in the subclass.
        """
        raise NotImplementedError

    def _verify_json_format_args(self,
                                 params: Union[str, dict]) -> Union[str, dict]:
        """Verify the parameters of the function call"""
        try:
            if isinstance(params, str):
                params_json = json5.loads(params)
            else:
                params_json = params
            for param in self.parameters:
                if 'required' in param and param['required']:
                    if param['name'] not in params_json:
                        raise ValueError('Parameters %s is required!' %
                                         param['name'])
            return params_json
        except Exception:
            raise ValueError('Parameters cannot be converted to Json Format!')

    def _build_function(self) -> dict:
        return {
            'name_for_human': self.name_for_human,
            'name': self.name,
            'description': self.description,
            'parameters': self.parameters,
            'args_format': self.args_format
        }
