from abc import ABC
from typing import List

from qwen_agent.llm.base import BaseChatModel

from .schema import ASSISTANT, CONTENT, FUNCTION, ROLE, SYSTEM, USER, Message


class BaseTextChatModel(BaseChatModel, ABC):

    def _preprocess_messages(self, messages: List[Message]) -> List[Message]:
        messages = super()._preprocess_messages(messages)
        messages = self._convert_to_text_messages(messages)
        return messages

    def _postprocess_messages_for_func_call(
            self, messages: List[Message]) -> List[Message]:
        messages = super()._postprocess_messages_for_func_call(messages)
        messages = self._convert_to_text_messages(messages)
        return messages

    def _convert_to_text_messages(self,
                                  messages: List[Message]) -> List[Message]:
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
