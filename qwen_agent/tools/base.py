from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union

import json5

TOOL_REGISTRY = {}


def register_tool(name):

    def decorator(cls):
        if name in TOOL_REGISTRY:
            raise ValueError(
                f'tool {name} has a duplicate name! Please ensure that the tool name is unique.'
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

        self.name_for_human = self.cfg.get('name_for_human', self.name)
        if not hasattr(self, 'args_format'):
            self.args_format = self.cfg.get('args_format', '此工具的输入应为JSON对象。')
        self.function = self._build_function()
        self.file_access = False

    @abstractmethod
    def call(self, params: Union[str, dict], **kwargs):
        """
        The interface for calling tools

        :param params: the parameters of func_call
        :param kwargs: additional parameters for calling tools
        :return: the result returned by the tool, implemented in the subclass
        """
        raise NotImplementedError

    def _verify_json_format_args(self,
                                 params: Union[str, dict]) -> Union[str, dict]:
        """
        Verify the parameters of the function call

        :param params: the parameters of func_call
        :return: the str params or the legal dict params
        """
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

    def _build_function(self):
        """
        The dict format after applying the template to the function, such as oai format

        """
        return {
            'name_for_human': self.name_for_human,
            'name': self.name,
            'description': self.description,
            'parameters': self.parameters,
            'args_format': self.args_format
        }
