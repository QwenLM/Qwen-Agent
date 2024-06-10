import copy
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.agents.assistant import Assistant
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import DEFAULT_SYSTEM_MESSAGE, FUNCTION, USER, ContentItem, Message
from qwen_agent.settings import MAX_LLM_CALL_PER_RUN
from qwen_agent.tools import BaseTool

DEFAULT_NAME = 'Virtual Memory Agent'
DEFAULT_DESC = 'This agent can utilize tools to retrieve useful information from external resources or long conversation histories to aid in responding.'


class VirtualMemoryAgent(Assistant):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = DEFAULT_NAME,
                 description: Optional[str] = DEFAULT_DESC,
                 files: Optional[List[str]] = None,
                 rag_cfg: Optional[Dict] = None):
        # Add one default retrieval tool
        self.retrieval_tool_name = 'retrieval'
        super().__init__(function_list=[self.retrieval_tool_name] + (function_list or []),
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description,
                         files=files,
                         rag_cfg=rag_cfg)

    def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        ori_messages = messages
        messages = copy.deepcopy(messages)
        num_llm_calls_available = MAX_LLM_CALL_PER_RUN
        response = []
        while True and num_llm_calls_available > 0:
            num_llm_calls_available -= 1
            output_stream = self._call_llm(messages=self._format_file(messages) + response,
                                           functions=[func.function for func in self.function_map.values()])
            output: List[Message] = []
            for output in output_stream:
                if output:
                    yield response + output
            if output:
                response.extend(output)
            use_tool, action, action_input, _ = self._detect_tool(response[-1])
            if use_tool:
                observation = self._call_tool(action, action_input, messages=messages)
                if action == self.retrieval_tool_name:
                    # Filling the knowledge
                    messages = self._prepend_knowledge_prompt(messages=ori_messages, lang=lang, knowledge=observation)
                    observation = 'The relevant content has already been retrieved and updated in the previous system message.'
                fn_msg = Message(
                    role=FUNCTION,
                    name=action,
                    content=observation,
                )
                response.append(fn_msg)
                yield response
            else:
                break

    def _format_file(self, messages: List[Message], lang: str = 'en') -> List[Message]:
        if lang == 'en':
            file_prefix = '[file]({f_name})'
        else:
            file_prefix = '[文件]({f_name})'
        new_messages = []
        for msg in messages:
            if msg.role == USER and isinstance(msg.content, list):
                new_content = []
                for x in msg.content:
                    if x.file:
                        new_content.append(ContentItem(text=file_prefix.format(f_name=x.file)))
                    else:
                        new_content.append(x)
                new_messages.append(Message(role=msg.role, content=new_content, name=msg.name))
            else:
                new_messages.append(msg)
        return new_messages
