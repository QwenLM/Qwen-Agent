from typing import Dict, Optional

from .base import BaseChatModel
from .qwen_dashscope import QwenChatAtDS
from .qwen_oai import QwenChatAsOAI


def get_chat_model(cfg: Optional[Dict] = None) -> BaseChatModel:
    if 'model_server' in cfg and cfg['model_server'].strip().lower(
    ) == 'dashscope':
        llm = QwenChatAtDS(cfg)
    else:
        llm = QwenChatAsOAI(cfg)
    return llm
