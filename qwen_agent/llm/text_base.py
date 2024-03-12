from abc import ABC
from typing import List

from qwen_agent.llm.function_calling import BaseFnCallModel

from .schema import ASSISTANT, FUNCTION, SYSTEM, USER, Message


class BaseTextChatModel(BaseFnCallModel, ABC):

    def _preprocess_messages(self, messages: List[Message]) -> List[Message]:
        messages = super()._preprocess_messages(messages)
        messages = format_as_text_messages(messages)
        return messages

    def _postprocess_messages(self, messages: List[Message],
                              fncall_mode: bool) -> List[Message]:
        messages = super()._postprocess_messages(messages,
                                                 fncall_mode=fncall_mode)
        messages = format_as_text_messages(messages)
        return messages


def format_as_text_messages(
        multimodal_messages: List[Message]) -> List[Message]:
    text_messages = []
    for msg in multimodal_messages:
        assert msg.role in (USER, ASSISTANT, SYSTEM, FUNCTION)
        content = ''
        if isinstance(msg.content, str):
            content = msg.content
        elif isinstance(msg.content, list):
            for item in msg.content:
                if item.text:
                    content += item.text
                # Discard multimodal content such as files and images
        else:
            raise TypeError
        text_messages.append(
            Message(role=msg.role,
                    content=content,
                    name=msg.name if msg.role == FUNCTION else None,
                    function_call=msg.function_call))
    return text_messages
