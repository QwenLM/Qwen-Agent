from .base import BaseChatModel
from .qwen_dashscope import QwenChatAtDS
from .qwen_oai import QwenChatAsOAI


def get_chat_model(model: str, api_key: str,
                   model_server: str) -> BaseChatModel:
    if model_server.strip().lower() == 'dashscope':
        llm = QwenChatAtDS(model=model, api_key=api_key)
    else:
        llm = QwenChatAsOAI(model=model,
                            api_key=api_key,
                            model_server=model_server)
    return llm
