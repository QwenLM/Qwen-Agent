import torch
from models.base import HFModel


class LLM(HFModel):

    def __init__(self, model_path):
        super().__init__(model_path)

    def generate(self, input_text, stop_words=[], max_new_tokens=512):
        if isinstance(input_text, str):
            input_text = [input_text]

        input_ids = self.tokenizer(input_text)['input_ids']
        input_ids = torch.tensor(input_ids, device=self.model.device)
        gen_kwargs = {'max_new_tokens': max_new_tokens, 'do_sample': False}
        outputs = self.model.generate(input_ids, **gen_kwargs)
        s = outputs[0][input_ids.shape[1]:]
        output = self.tokenizer.decode(s, skip_special_tokens=True)

        for stop_str in stop_words:
            idx = output.find(stop_str)
            if idx != -1:
                output = output[:idx + len(stop_str)]

        return output
