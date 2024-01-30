from abc import ABC
from typing import Dict, List

from qwen_agent.llm.base import BaseChatModel

from .schema import ASSISTANT, CONTENT, FUNCTION, ROLE, SYSTEM, USER


class BaseTextChatModel(BaseChatModel, ABC):

    def _format_msg_for_llm(self, messages: List[Dict]) -> List[Dict]:
        new_messages = []
        for msg in messages:
            role = msg[ROLE]
            assert role in (USER, ASSISTANT, SYSTEM, FUNCTION)
            if role == FUNCTION:
                new_messages.append(msg)
                continue
            content = ''
            if isinstance(msg[CONTENT], str):
                content = msg[CONTENT]
            elif isinstance(msg[CONTENT], list):
                for item in msg[CONTENT]:
                    for k, v in item.items():
                        if k in ('box',
                                 'text'):  # all content values that qwen needs
                            content += v
            else:
                raise TypeError
            if f'{FUNCTION}_call' in msg:
                new_messages.append({
                    ROLE: role,
                    CONTENT: content,
                    f'{FUNCTION}_call': msg[f'{FUNCTION}_call']
                })
            else:
                new_messages.append({ROLE: role, CONTENT: content})

        return new_messages

    @staticmethod
    def _wrapper_text_to_message_list(text: str) -> List[Dict]:
        return [{ROLE: ASSISTANT, CONTENT: text}]
