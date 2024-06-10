from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation import GenerationConfig


class HFModel(object):

    def __init__(self, model_path):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(model_path,
                                                          trust_remote_code=True,
                                                          device_map='auto',
                                                          low_cpu_mem_usage=True).eval()
        self.model.generation_config = GenerationConfig.from_pretrained(model_path, trust_remote_code=True)
        self.model.generation_config.do_sample = False
