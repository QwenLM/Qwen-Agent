from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation import GenerationConfig

model_path_map = {
    'qwen-14b-chat': 'Qwen/Qwen-14B-Chat',
    'qwen-7b-chat-1.1': 'Qwen/Qwen-7B-Chat-1.1/',
    'qwen-1.8b-chat': 'Qwen/Qwen-1.8B-chat',
    'qwen-7b-chat': 'Qwen/Qwen-7B-Chat',
    'llama-2-7b-chat': 'meta-llama/Llama-2-7b-chat-hf',
    'llama-2-13b-chat': 'meta-llama/Llama-2-13b-chat-hf',
    'codellama-7b-instruct': 'codellama/CodeLlama-7b-Instruct-hf',
    'codellama-13b-instruct': 'codellama/CodeLlama-13b-Instruct-hf',
    'internlm': 'internlm/internlm-chat-7b-v1_1',
    'qwen-vl-chat': 'Qwen/Qwen-VL-Chat',
}


class HFModel(object):
    def __init__(self, model_name):
        self.model_name = model_name.lower()

        model_path = model_path_map.get(model_name, '')
        if not model_path:
            raise Exception('No available model.')

        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(model_path, trust_remote_code=True, device_map='auto', low_cpu_mem_usage=True).eval()
        self.model.generation_config = GenerationConfig.from_pretrained(model_path, trust_remote_code=True)
        self.model.generation_config.do_sample = False
