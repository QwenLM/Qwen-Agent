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
from typing import Dict, Iterator, List, Literal, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import DEFAULT_SYSTEM_MESSAGE, FUNCTION, Message
from qwen_agent.memory import Memory
from qwen_agent.settings import MAX_LLM_CALL_PER_RUN
from qwen_agent.tools import BaseTool
from qwen_agent.utils.utils import extract_files_from_messages


class FnCallAgent(Agent):
    """This is a widely applicable function call agent integrated with llm and tool use ability."""

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 files: Optional[List[str]] = None,
                 **kwargs):
        """Initialization the agent.

        Args:
            function_list: One list of tool name, tool configuration or Tool object,
              such as 'code_interpreter', {'name': 'code_interpreter', 'timeout': 10}, or CodeInterpreter().
            llm: The LLM model configuration or LLM model object.
              Set the configuration as {'model': '', 'api_key': '', 'model_server': ''}.
            system_message: The specified system message for LLM chat.
            name: The name of this agent.
            description: The description of this agent, which will be used for multi_agent.
            files: A file url list. The initialized files for the agent.
        """
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description)

        if not hasattr(self, 'mem'):
            # Default to use Memory to manage files
            if 'qwq' in self.llm.model.lower() or 'qvq' in self.llm.model.lower() or 'qwen3' in self.llm.model.lower():
                if 'dashscope' in self.llm.model_type:
                    mem_llm = {
                        'model': 'qwen-turbo',
                        'model_type': 'qwen_dashscope',
                        'generate_cfg': {
                            'max_input_tokens': 30000
                        }
                    }
                else:
                    mem_llm = None
            else:
                mem_llm = self.llm
            self.mem = Memory(llm=mem_llm, files=files, **kwargs)

    def _run(self, messages: List[Message], lang: Literal['en', 'zh'] = 'en', **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)
        num_llm_calls_available = MAX_LLM_CALL_PER_RUN
        response = []
        while True and num_llm_calls_available > 0:
            num_llm_calls_available -= 1

            extra_generate_cfg = {'lang': lang}
            if kwargs.get('seed') is not None:
                extra_generate_cfg['seed'] = kwargs['seed']
            output_stream = self._call_llm(messages=messages,
                                           functions=[func.function for func in self.function_map.values()],
                                           extra_generate_cfg=extra_generate_cfg)
            output: List[Message] = []
            for output in output_stream:
                if output:
                    yield response + output
            if output:
                response.extend(output)
                messages.extend(output)
                used_any_tool = False
                for out in output:
                    use_tool, tool_name, tool_args, _ = self._detect_tool(out)
                    if use_tool:
                        tool_result = self._call_tool(tool_name, tool_args, messages=messages, **kwargs)
                        fn_msg = Message(role=FUNCTION,
                                         name=tool_name,
                                         content=tool_result,
                                         extra={'function_id': out.extra.get('function_id', '1')})
                        messages.append(fn_msg)
                        response.append(fn_msg)
                        yield response
                        used_any_tool = True
                if not used_any_tool:
                    break
        yield response

    def _call_tool(self, tool_name: str, tool_args: Union[str, dict] = '{}', **kwargs) -> str:
        if tool_name not in self.function_map:
            return f'Tool {tool_name} does not exists.'
        # Temporary plan: Check if it is necessary to transfer files to the tool
        # Todo: This should be changed to parameter passing, and the file URL should be determined by the model
        if self.function_map[tool_name].file_access:
            assert 'messages' in kwargs
            files = extract_files_from_messages(kwargs['messages'], include_images=True) + self.mem.system_files
            return super()._call_tool(tool_name, tool_args, files=files, **kwargs)
        else:
            return super()._call_tool(tool_name, tool_args, **kwargs)
