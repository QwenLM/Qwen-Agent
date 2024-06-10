import torch
from models.base import HFModel


class Qwen(HFModel):

    def __init__(self, model_path):
        super().__init__(model_path)

    def generate(self, input_text, stop_words=[]):
        im_end = '<|im_end|>'
        if im_end not in stop_words:
            stop_words = stop_words + [im_end]
        stop_words_ids = [self.tokenizer.encode(w) for w in stop_words]

        input_ids = torch.tensor([self.tokenizer.encode(input_text)]).to(self.model.device)
        output = self.model.generate(input_ids, stop_words_ids=stop_words_ids)
        output = output.tolist()[0]
        output = self.tokenizer.decode(output, errors='ignore')
        assert output.startswith(input_text)
        output = output[len(input_text):].replace('<|endoftext|>', '').replace(im_end, '')

        return output


class QwenVL(HFModel):

    def __init__(self, model_path):
        super().__init__(model_path)

    def generate(self, inputs: list):
        query = self.tokenizer.from_list_format(inputs)
        response, _ = self.model.chat(self.tokenizer, query=query, history=None)

        return response
