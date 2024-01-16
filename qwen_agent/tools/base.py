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

        # schema: Format of tools, default to oai format, in case there is a need for other formats
        self.schema = self.cfg.get('schema', 'oai')
        self.function = self._build_function()

    @abstractmethod
    def call(self, params: str, **kwargs):
        """
        The interface for calling tools

        :param params: the parameters of func_call
        :param kwargs: additional parameters for calling tools
        :return: the result returned by the tool, implemented in the subclass
        """
        raise NotImplementedError

    def _verify_args(self, params: str) -> Union[str, dict]:
        """
        Verify the parameters of the function call

        :param params: the parameters of func_call
        :return: the str params or the legal dict params
        """
        try:
            params_json = json5.loads(params)
            for param in self.parameters:
                if 'required' in param and param['required']:
                    if param['name'] not in params_json:
                        return params
            return params_json
        except Exception:
            return params

    def _build_function(self):
        """
        The dict format after applying the template to the function, such as oai format

        """
        if self.schema == 'oai':
            function = {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': {},
                    'required': [],
                },
            }
            for para in self.parameters:
                function['parameters']['properties'][para['name']] = {
                    'type': para['type'],
                    'description': para['description']
                }
                if 'required' in para and para['required']:
                    function['parameters']['required'].append(para['name'])
        else:
            function = {
                'name': self.name,
                'description': self.description,
                'parameters': self.parameters
            }

        return function
