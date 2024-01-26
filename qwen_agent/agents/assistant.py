import json
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import CONTENT, DEFAULT_SYSTEM_MESSAGE, ROLE, SYSTEM
from qwen_agent.log import logger
from qwen_agent.memory import Memory
from qwen_agent.utils.utils import format_knowledge_to_source_and_content

KNOWLEDGE_SNIPPET_ZH = """## 来自 {source} 的内容：

```
{content}
```"""
KNOWLEDGE_TEMPLATE_ZH = """

# 知识库

{knowledge}"""

KNOWLEDGE_SNIPPET_EN = """## The content from {source}:

```
{content}
```"""
KNOWLEDGE_TEMPLATE_EN = """

# Knowledge Base

{knowledge}"""

KNOWLEDGE_SNIPPET = {'zh': KNOWLEDGE_SNIPPET_ZH, 'en': KNOWLEDGE_SNIPPET_EN}
KNOWLEDGE_TEMPLATE = {'zh': KNOWLEDGE_TEMPLATE_ZH, 'en': KNOWLEDGE_TEMPLATE_EN}


class Assistant(Agent):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 files: Optional[List[str]] = None):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message)

        # default to use Memory to manage files
        self.mem = Memory(llm=self.llm, files=files)

    def _run(self,
             messages: List[Dict],
             lang: str = 'zh',
             max_ref_token: int = 4000,
             **kwargs) -> Iterator[List[Dict]]:
        system_prompt = ''

        # retrieval knowledge from files
        *_, last = self.mem.run(messages=messages, max_ref_token=max_ref_token)
        knowledge = last[-1][CONTENT]
        logger.debug(knowledge)
        if knowledge:
            knowledge = format_knowledge_to_source_and_content(knowledge)
            snippets = []
            for k in knowledge:
                snippets.append(KNOWLEDGE_SNIPPET[lang].format(
                    source=k['source'], content=k['content']))
            system_prompt += KNOWLEDGE_TEMPLATE[lang].format(
                knowledge='\n\n'.join(snippets))

        if messages[0][ROLE] == SYSTEM:
            messages[0][CONTENT] += system_prompt
        else:
            messages.insert(0, {ROLE: SYSTEM, CONTENT: system_prompt})

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

    def _call_tool(self,
                   tool_name: str,
                   tool_args: Union[str, dict] = '{}',
                   **kwargs):
        # Temporary plan: Check if it is necessary to transfer files to the tool
        # Todo: This should be changed to parameter passing, and the file URL should be determined by the model
        if self.function_map[tool_name].file_access:
            return super()._call_tool(tool_name,
                                      tool_args,
                                      files=self.mem.files,
                                      **kwargs)
        else:
            return super()._call_tool(tool_name, tool_args, **kwargs)
