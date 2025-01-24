import copy
from typing import Dict, Iterator, List, Optional, Union

import json5

from qwen_agent.agents import Assistant
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import DEFAULT_SYSTEM_MESSAGE, SYSTEM, USER, ContentItem, Message
from qwen_agent.tools import BaseTool

MEMORY_PROMPT = """
在对话过程中，你可以随时使用storage工具来存储你认为需要记住的信息，同时也随时可以读取曾经可能存储了的历史信息。
这将有助于你在和用户的长对话中，记住某些重要的信息，比如用户的喜好、特殊信息、或重大事件等。
关于数据存取，有以下两点建议：
1. 存一条数据的key尽量简洁易懂，可以用所记录内容的关键词；
2. 如果忘记存过什么数据，可以使用scan查看记录过哪些数据；

此处展示当前你存入的所有信息，因此你可以省去专门读取数据的操作：
<info>
{storage_info}
</info>

你的记忆很短暂，请频繁的调用工具存储重要对话内容。
"""


class MemoAssistant(Assistant):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 files: Optional[List[str]] = None):
        function_list = function_list or []
        super().__init__(function_list=['storage'] + function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description,
                         files=files)

    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             max_ref_token: int = 4000,
             **kwargs) -> Iterator[List[Message]]:
        new_message = self._prepend_storage_info_to_sys(messages)
        new_message = self._truncate_dialogue_history(new_message)

        for rsp in super()._run(new_message, lang, max_ref_token, **kwargs):
            yield rsp

    def _prepend_storage_info_to_sys(self, messages: List[Message]) -> List[Message]:
        messages = copy.deepcopy(messages)
        all_kv = {}
        # Obtained from message, with the purpose of facilitating control of information volume
        for msg in messages:
            if msg.function_call and msg.function_call.name == 'storage':
                try:
                    param = json5.loads(msg.function_call.arguments)
                except Exception:
                    continue
                if param['operate'] in ['put', 'update']:
                    all_kv[param['key']] = param['value']
                elif param['operate'] == 'delete' and param['key'] in all_kv:
                    all_kv.pop(param['key'])
                else:
                    pass
        all_kv_str = '\n'.join([f'{k}: {v}' for k, v in all_kv.items()])
        sys_memory_prompt = MEMORY_PROMPT.format(storage_info=all_kv_str)
        if messages[0].role == SYSTEM:
            if isinstance(messages[0].content, str):
                messages[0].content += '\n\n' + sys_memory_prompt
            else:
                assert isinstance(messages[0].content, list)
                messages[0].content += [ContentItem(text='\n\n' + sys_memory_prompt)]
        else:
            messages = [Message(role=SYSTEM, content=sys_memory_prompt)] + messages
        return messages

    def _truncate_dialogue_history(self, messages: List[Message]) -> List[Message]:
        # This simulates a very small window, retaining only the most recent three rounds of conversation
        new_messages = []
        available_turn = 4
        k = len(messages) - 1
        while k > -1:
            msg = messages[k]
            if available_turn == 0:
                break
            if msg.role == USER:
                available_turn -= 1
            new_messages = [msg] + new_messages
            k -= 1

        if k > -1 and messages[0].role == SYSTEM:
            new_messages = [messages[0]] + new_messages

        return new_messages
