from typing import Dict, Optional

from .base import BaseChatModel
from .qwen_dashscope import QwenChatAtDS
from .qwen_oai import QwenChatAsOAI
from .qwenvl_dashscope import QwenVLChatAtDS


def get_chat_model(cfg: Optional[Dict] = None) -> BaseChatModel:
    """

    :param cfg: cfg example:
            llm_cfg = {
            # Use the model service provided by DashScope:
            'model': 'qwen-max',
            'model_server': 'dashscope',
            # Use your own model service compatible with OpenAI API:
            # 'model': 'Qwen',
            # 'model_server': 'http://127.0.0.1:7905/v1',

            # (Optional) LLM hyper-paramters:
            'generate_cfg': {
                'top_p': 0.8
            }
        }
    :return: BaseChatModel
    """
    if 'model' in cfg and cfg['model'].strip().lower().startswith('qwen-vl'):
        if 'model_server' in cfg:
            assert cfg['model_server'].strip().lower(
            ) == 'dashscope', 'Can only access qwen-vl through dashscope api'
        llm = QwenVLChatAtDS(cfg)
    elif 'model_server' in cfg and cfg['model_server'].strip().lower(
    ) == 'dashscope':
        llm = QwenChatAtDS(cfg)
    else:
        llm = QwenChatAsOAI(cfg)
    return llm
