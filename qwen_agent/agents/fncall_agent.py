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
import json
import os
from typing import Dict, Iterator, List, Literal, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import DEFAULT_SYSTEM_MESSAGE, FUNCTION, Message
from qwen_agent.memory import Memory
from qwen_agent.settings import MAX_LLM_CALL_PER_RUN
from qwen_agent.tools import BaseTool
from qwen_agent.utils.utils import extract_files_from_messages

# 工具调用数量限制（每轮）
MAX_TOOL_CALLS_PER_TURN = int(os.getenv('MAX_TOOL_CALLS_PER_TURN', '8'))


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
        handled_fn_ids = set()  # ✅ 新增：避免重复
        self._fn_seq = getattr(self, '_fn_seq', 0)  # ✅ 新增：自增计数器
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
                tools_used_this_turn = 0  # 记录本轮已触发的工具数量

                for out in output:
                    use_tool, tool_name, tool_args, _ = self._detect_tool(out)
                    if use_tool:
                        # 超过单轮上限则友好告知并停止本轮继续触发工具
                        if tools_used_this_turn >= MAX_TOOL_CALLS_PER_TURN:
                            warn = Message(
                                role='assistant',
                                content=f'本轮工具调用数量已达上限（MAX_TOOL_CALLS_PER_TURN={MAX_TOOL_CALLS_PER_TURN}），暂停进一步调用。'
                            )
                            messages.append(warn)
                            response.append(warn)
                            # 不再继续这一轮的更多工具调用
                            break
                        
                        # ✅ 额外护栏：确保工具名在已注册工具列表中
                        if tool_name not in self.function_map:
                            continue  # 模型口误的工具名直接跳过
                        
                        _extra = (getattr(out, 'extra', {}) or {})
                        fn_id = _extra.get('function_id')
                        # ✅ function_id 缺失时，避免不同工具调用都落到 '1' 被去重掉
                        if not fn_id:
                            self._fn_seq += 1
                            fn_id = f'auto_{self._fn_seq}'  # 确保不同次调用有不同id
                        
                        if fn_id in handled_fn_ids:
                            continue  # ✅ 已处理过的 function_id，跳过

                        # --- 仅当 arguments 是"完整可解析的 JSON"时才触发工具调用 ---
                        args_ready = False
                        parsed_args = tool_args
                        if isinstance(tool_args, str):
                            try:
                                parsed_args = json.loads(tool_args)
                                args_ready = True
                            except Exception:
                                args_ready = False
                        elif isinstance(tool_args, dict):
                            args_ready = True
                        else:
                            args_ready = False

                        if not args_ready:
                            # 还在流式拼接半截 JSON，等待下一批增量
                            continue

                        # ✅ 关键修复：往下传"字符串"而不是"dict"
                        tool_args_to_pass = (
                            json.dumps(parsed_args, ensure_ascii=False)
                            if isinstance(parsed_args, dict) else parsed_args
                        )
                        tool_result = self._call_tool(tool_name, tool_args_to_pass, messages=messages, **kwargs)

                        # --- 兜底 out.extra 为空的情况，避免 NoneType.get 崩溃 ---
                        fn_msg = Message(
                            role=FUNCTION,
                            name=tool_name,
                            content=tool_result,
                            extra={'function_id': fn_id}
                        )
                        messages.append(fn_msg)
                        response.append(fn_msg)
                        handled_fn_ids.add(fn_id)  # ✅ 标记已处理
                        # 成功触发一个工具后：
                        tools_used_this_turn += 1
                        yield response
                        used_any_tool = True
                if not used_any_tool:
                    break
        # 配额用尽的"收尾消息"
        if num_llm_calls_available == 0:
            tail = Message(
                role='assistant',
                content=f'已达到最大迭代步数（MAX_LLM_CALL_PER_RUN={MAX_LLM_CALL_PER_RUN}），终止本轮。若需继续请重试或提高上限。'
            )
            messages.append(tail)
            response.append(tail)

        yield response

    def _call_tool(self, tool_name: str, tool_args: Union[str, dict] = '{}', **kwargs) -> str:
        # ✅ 强制字符串化，防止 dict 传下去
        if isinstance(tool_args, dict):
            tool_args = json.dumps(tool_args, ensure_ascii=False)
            
        if tool_name not in self.function_map:
            return f'Tool {tool_name} does not exists.'
        
        try:
            # Temporary plan: Check if it is necessary to transfer files to the tool
            # Todo: This should be changed to parameter passing, and the file URL should be determined by the model
            if self.function_map[tool_name].file_access:
                assert 'messages' in kwargs
                files = extract_files_from_messages(kwargs['messages'], include_images=True) + self.mem.system_files
                result = super()._call_tool(tool_name, tool_args, files=files, **kwargs)
            else:
                result = super()._call_tool(tool_name, tool_args, **kwargs)
        except Exception as e:
            # 避免把异常对象直接塞进 Message.content
            return f'Error when calling `{tool_name}`: {type(e).__name__}: {e}'
        
        # 防御：工具可能返回 dict
        if not isinstance(result, str):
            try:
                return json.dumps(result, ensure_ascii=False)
            except Exception:
                return str(result)
        return result
