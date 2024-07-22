import copy
import os
from typing import Iterator, List

from qwen_agent.llm.base import register_llm
from qwen_agent.llm.oai import TextChatAtOAI
from qwen_agent.llm.schema import Message
from qwen_agent.utils.utils import encode_image_as_base64


def _convert_local_images_to_base64(messages: List[Message]) -> List[Message]:
    messages_new = []
    for msg in messages:
        if isinstance(msg.content, list):
            msg = copy.deepcopy(msg)
            for item in msg.content:
                t, v = item.get_type_and_value()
                if t == 'image':
                    if (not v.startswith(('http://', 'https://', 'data:'))) and os.path.exists(v):
                        item.image = encode_image_as_base64(v, max_short_side_length=1080)
        else:
            assert isinstance(msg.content, str)
        messages_new.append(msg)
    return messages_new


@register_llm('qwenvl_oai')
class QwenVLChatAtOAI(TextChatAtOAI):

    @property
    def support_multimodal_input(self) -> bool:
        return True

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool,
        generate_cfg: dict,
    ) -> Iterator[List[Message]]:
        messages = _convert_local_images_to_base64(messages)
        return super()._chat_stream(messages=messages, delta_stream=delta_stream, generate_cfg=generate_cfg)

    def _chat_no_stream(
        self,
        messages: List[Message],
        generate_cfg: dict,
    ) -> List[Message]:
        messages = _convert_local_images_to_base64(messages)
        return super()._chat_no_stream(messages=messages, generate_cfg=generate_cfg)
