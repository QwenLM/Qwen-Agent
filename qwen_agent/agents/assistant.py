import copy
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import (CONTENT, DEFAULT_SYSTEM_MESSAGE, FUNCTION,
                                   ROLE, SYSTEM, Message)
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

MAX_LLM_CALL_PER_RUN = 8


class Assistant(Agent):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 files: Optional[List[str]] = None):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description)

        # default to use Memory to manage files
        self.mem = Memory(llm=self.llm, files=files)

    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             max_ref_token: int = 4000,
             **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)

        # retrieval knowledge from files
        *_, last = self.mem.run(messages=messages, max_ref_token=max_ref_token)
        knowledge = last[-1][CONTENT]
        logger.debug(f'{type(knowledge)}: {knowledge}')
        if knowledge:
            knowledge = format_knowledge_to_source_and_content(knowledge)
            logger.debug(f'{type(knowledge)}: {knowledge}')
        else:
            knowledge = []
        snippets = []
        for k in knowledge:
            snippets.append(KNOWLEDGE_SNIPPET[lang].format(
                source=k['source'], content=k['content']))
        if snippets:
            knowledge_prompt = KNOWLEDGE_TEMPLATE[lang].format(
                knowledge='\n\n'.join(snippets))
            if messages[0][ROLE] == SYSTEM:
                messages[0][CONTENT] += knowledge_prompt
            else:
                messages = [Message(role=SYSTEM, content=knowledge_prompt)
                            ] + messages

        num_llm_calls_available = MAX_LLM_CALL_PER_RUN
        response = []
        while True and num_llm_calls_available > 0:
            num_llm_calls_available -= 1
            output_stream = self._call_llm(
                messages=messages,
                functions=[
                    func.function for func in self.function_map.values()
                ])
            output: List[Message] = []
            for output in output_stream:
                if output:
                    yield response + output
            if output:
                response.extend(output)
                messages.extend(output)
            use_tool, action, action_input, _ = self._detect_tool(response[-1])
            if use_tool:
                observation = self._call_tool(action,
                                              action_input,
                                              messages=messages)
                fn_msg = Message(
                    role=FUNCTION,
                    name=action,
                    content=observation,
                )
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
            assert 'messages' in kwargs
            files = self.mem.get_all_files_of_messages(
                kwargs['messages']) + self.mem.system_files
            return super()._call_tool(tool_name,
                                      tool_args,
                                      files=files,
                                      **kwargs)
        else:
            return super()._call_tool(tool_name, tool_args, **kwargs)
