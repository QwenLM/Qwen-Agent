from abc import ABC
from typing import List, Literal

from qwen_agent.llm.function_calling import BaseFnCallModel
from qwen_agent.llm.schema import Message
from qwen_agent.utils.utils import format_as_text_message


class BaseTextChatModel(BaseFnCallModel, ABC):

    def _preprocess_messages(self, messages: List[Message], lang: Literal['en', 'zh']) -> List[Message]:
        messages = super()._preprocess_messages(messages, lang=lang)
        # The upload info is already added by super()._preprocess_messages
        messages = [format_as_text_message(msg, add_upload_info=False) for msg in messages]
        return messages

    def _postprocess_messages(
        self,
        messages: List[Message],
        fncall_mode: bool,
        generate_cfg: dict,
    ) -> List[Message]:
        messages = super()._postprocess_messages(messages, fncall_mode=fncall_mode, generate_cfg=generate_cfg)
        messages = [format_as_text_message(msg, add_upload_info=False) for msg in messages]
        return messages
