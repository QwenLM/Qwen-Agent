import json
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import (CONTENT, DEFAULT_SYSTEM_MESSAGE, FILE, ROLE,
                                   SYSTEM, USER)
from qwen_agent.log import logger
from qwen_agent.memory import Memory

KNOWLEDGE_TEMPLATE_ZH = """

# 知识库

{knowledge}

"""

KNOWLEDGE_TEMPLATE_EN = """

# Knowledge Base

{knowledge}

"""

KNOWLEDGE_TEMPLATE = {'zh': KNOWLEDGE_TEMPLATE_ZH, 'en': KNOWLEDGE_TEMPLATE_EN}

SPECIAL_PREFIX_TEMPLATE = {
    'zh': '(你可以使用工具：[{tool_names}])',
    'en': '(You have access to tools: [{tool_names}])',
}


class Assistant(Agent):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 storage_path: Optional[str] = None,
                 files: Optional[List[str]] = None):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description)

        # default to use Memory to manage files
        self.mem = Memory(llm=self.llm, storage_path=storage_path)

        self.files = files or []
        for file in self.files:
            if not file.lower().endswith('pdf'):
                raise ValueError(
                    'Currently, only PDF documents can be added as knowledge')
            # save file to knowledge base
            try:
                *_, last = self.mem.run(messages=[{
                    ROLE: USER,
                    CONTENT: [{
                        FILE: file
                    }]
                }],
                                        ignore_cache=True)
            except Exception:
                raise ValueError(f'Failed to parse document {file}.')

    def _run(self,
             messages: List[Dict],
             lang: str = 'zh',
             max_ref_token: int = 4000,
             **kwargs) -> Iterator[List[Dict]]:
        system_prompt = ''
        if self.files:
            # retrieval knowledge from files
            *_, last = self.mem.run(messages=messages,
                                    max_ref_token=max_ref_token,
                                    files=self.files)
            knowledge = last[-1][CONTENT]
            system_prompt += KNOWLEDGE_TEMPLATE[lang].format(
                knowledge=knowledge)

        query_prefix = ''
        if self.function_map:
            # This query_prefix may discard
            tool_names = ','.join(tool.name
                                  for tool in self.function_map.values())
            query_prefix = SPECIAL_PREFIX_TEMPLATE[lang].format(
                tool_names=tool_names)

        if messages[0][ROLE] == SYSTEM:
            messages[0][CONTENT] += system_prompt
        else:
            messages.insert(0, {ROLE: SYSTEM, CONTENT: system_prompt})

        # concat the new messages
        messages[-1][CONTENT] = query_prefix + messages[-1][CONTENT]

        max_turn = 5
        response = []
        while True and max_turn > 0:
            max_turn -= 1
            output_stream = self._call_llm(
                messages=messages,
                functions=[
                    func.function for func in self.function_map.values()
                ])
            output = []
            for output in output_stream:
                yield response + output
            response.extend(output)
            messages.extend(output)
            logger.debug(json.dumps(response, ensure_ascii=False, indent=4))
            use_tool, action, action_input, _ = self._detect_tool(response[-1])
            if use_tool:
                observation = self._call_tool(action, action_input)
                fn_msg = {
                    'role': 'function',
                    'name': action,
                    'content': observation,
                }
                messages.append(fn_msg)
                response.append(fn_msg)
                yield response
            else:
                break
