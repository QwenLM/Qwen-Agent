from parser import InternLMReActParser, ReActParser

from models import LLM, Qwen, QwenDashscopeVLModel, QwenVL
from prompt import InternLMReAct, LlamaReAct, QwenReAct

react_prompt_map = {
    'qwen': QwenReAct,
    'llama': LlamaReAct,
    'internlm': InternLMReAct,
}

react_parser_map = {
    'qwen': ReActParser,
    'llama': ReActParser,
    'internlm': InternLMReActParser,
}

model_map = {'qwen': Qwen, 'llama': LLM, 'internlm': LLM, 'qwen-vl-chat': QwenVL}

model_type_map = {
    'qwen-72b-chat': 'qwen',
    'qwen-14b-chat': 'qwen',
    'qwen-1.8b-chat': 'qwen',
    'qwen-7b-chat': 'qwen',
    'llama-2-7b-chat': 'llama',
    'llama-2-13b-chat': 'llama',
    'codellama-7b-instruct': 'llama',
    'codellama-13b-instruct': 'llama',
    'internlm-7b-chat-1.1': 'internlm',
    'internlm-20b-chat': 'internlm',
    'qwen-vl-chat': 'qwen-vl-chat',
}

model_path_map = {
    'qwen-72b-chat': 'Qwen/Qwen-72B-Chat',
    'qwen-14b-chat': 'Qwen/Qwen-14B-Chat',
    'qwen-7b-chat': 'Qwen/Qwen-7B-Chat',
    'qwen-1.8b-chat': 'Qwen/Qwen-1_8B-Chat',
    'llama-2-7b-chat': 'meta-llama/Llama-2-7b-chat-hf',
    'llama-2-13b-chat': 'meta-llama/Llama-2-13b-chat-hf',
    'codellama-7b-instruct': 'codellama/CodeLlama-7b-Instruct-hf',
    'codellama-13b-instruct': 'codellama/CodeLlama-13b-Instruct-hf',
    'internlm-7b-chat-1.1': 'internlm/internlm-chat-7b-v1_1',
    'internlm-20b-chat': 'internlm/internlm-chat-20b',
    'qwen-vl-chat': 'Qwen/Qwen-VL-Chat',
}


def get_react_prompt(model_name, query, lang, upload_fname_list):
    react_prompt_cls = react_prompt_map.get(model_type_map[model_name], QwenReAct)
    return react_prompt_cls(query, lang, upload_fname_list)


def get_react_parser(model_name):
    react_parser_cls = react_parser_map.get(model_type_map[model_name], ReActParser)
    return react_parser_cls()


def get_model(model_name):
    if model_name in ['qwen-vl-plus']:
        return QwenDashscopeVLModel(model=model_name)
    model_path = model_path_map.get(model_name, None)
    model_cls = model_map.get(model_type_map[model_name], LLM)
    return model_cls(model_path)
