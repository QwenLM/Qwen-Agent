from abc import ABC
from typing import List

from qwen_agent.llm.base import BaseChatModel

from .schema import ASSISTANT, CONTENT, FUNCTION, ROLE, SYSTEM, USER, Message


class BaseTextChatModel(BaseChatModel, ABC):

    def _format_msg_for_llm(self, messages: List[Message]) -> List[Message]:
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
                    if item.text:
                        content += item.text
            else:
                raise TypeError

            new_messages.append(
                Message(role=role,
                        content=content,
                        function_call=msg.function_call))

        return new_messages
