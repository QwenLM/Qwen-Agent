from typing import Iterator, List

from qwen_agent.llm.base import register_llm
from qwen_agent.llm.oai import TextChatAtOAI
from qwen_agent.llm.schema import Message


def _check_supported_input(messages: List[Message]):
    for msg in messages:
        if isinstance(msg.content, list):
            for item in msg.content:
                t, v = item.get_type_and_value()
                if t not in ('text', 'image'):
                    raise ValueError(f'QwenVLChatAtOAI does support content type "{t}" (value="{v}").')
                if t == 'image':
                    if not v.startswith(('http://', 'https://', 'data:')):
                        raise ValueError('QwenVLChatAtOAI currently does support local image paths. '
                                         f'Received image="{v}", but an http(s) URL or base64 is expected.')
        else:
            assert isinstance(msg.content, str)


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
        _check_supported_input(messages)
        return super()._chat_stream(messages=messages, delta_stream=delta_stream, generate_cfg=generate_cfg)

    def _chat_no_stream(
        self,
        messages: List[Message],
        generate_cfg: dict,
    ) -> List[Message]:
        _check_supported_input(messages)
        return super()._chat_no_stream(messages=messages, generate_cfg=generate_cfg)
