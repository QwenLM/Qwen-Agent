# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
from pprint import pformat
from threading import Thread
from typing import Dict, Iterator, List, Optional

from qwen_agent.llm.base import register_llm
from qwen_agent.llm.function_calling import BaseFnCallModel
from qwen_agent.llm.schema import ASSISTANT, Message
from qwen_agent.llm.schema import IMAGE, AUDIO, VIDEO
from qwen_agent.log import logger


@register_llm('transformers')
class Transformers(BaseFnCallModel):
    """
    Transformers class supports loading models from `transformers` library.

    Example of creating an assistant:
        llm_cfg = {
            'model': 'Qwen/Qwen3-4B',
            'model_type': 'transformers',
            'device': 'cuda'
        }
        bot = Assistant(llm=llm_cfg, ...)
    """
    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)

        if 'model' not in cfg:
            raise ValueError('Please provide the model id or directory through `model` in cfg.')

        try:
            import transformers
            from transformers import AutoConfig, AutoTokenizer, AutoProcessor, AutoModelForCausalLM
            from transformers import PreTrainedTokenizer, PreTrainedTokenizerFast
        except ImportError as e:
            raise ImportError('Could not import classes from transformers. '
                              'Please install it with `pip install -U transformers`') from e
        
        self.hf_config = AutoConfig.from_pretrained(cfg['model'])
        arch = self.hf_config.architectures[0]
        if len(self.hf_config.architectures) > 1:
            logger.warning(f'The config for the transformers model type contains more than one architecture, choosing the first: {arch}')

        # try loading a processor, if got a tokenizer, regarding the model as text-only
        processor = AutoProcessor.from_pretrained(cfg['model'])
        if isinstance(processor, (PreTrainedTokenizer, PreTrainedTokenizerFast)):
            logger.info(f'Regarding the transformers model as text-only since its processor is a tokenizer.')
            self.tokenizer = processor
            self._support_multimodal_input = False
        else:
            self.processor = processor
            self.tokenizer = self.processor.tokenizer
            self._support_multimodal_input = True

        model_cls = getattr(transformers, arch)
        self.hf_model = model_cls.from_pretrained(cfg['model'], config=self.hf_config, torch_dtype='auto').to(cfg.get('device', 'cpu'))

    @property
    def support_multimodal_input(self) -> bool:
        return self._support_multimodal_input
    
    @property
    def support_audio_input(self) -> bool:
        return self._support_multimodal_input

    def _get_streamer(self):
        from transformers import TextIteratorStreamer

        return TextIteratorStreamer(self.tokenizer, timeout=60.0, skip_prompt=True, skip_special_tokens=True)

    def _get_inputs(self, messages: List[Message]):
        import torch
        
        messages_plain = [message.model_dump() for message in messages]
        if not self.support_multimodal_input:
            input_ids = self.tokenizer.apply_chat_template(messages_plain, add_generation_prompt=True, return_tensors='pt')
            inputs = dict(input_ids=input_ids, attention_mask=torch.ones_like(input_ids))
        else:
            for message in messages_plain:
                for content_item in message['content']:
                    content_item['type'] = [type_ for type_ in ('text', IMAGE, AUDIO, VIDEO) if type_ in content_item][0]
            
            has_vision = False
            audio_paths = []
            for message in messages_plain:
                for content_item in message['content']:
                    if content_item['type'] in (IMAGE, VIDEO):
                        has_vision = True
                    if content_item['type'] in (AUDIO,):
                        audio_paths.append(content_item[AUDIO])
            
            prompt = self.processor.apply_chat_template(messages_plain, add_generation_prompt=True, tokenize=False)
            processor_kwargs = {'text': prompt}
            
            if has_vision:
                from qwen_vl_utils import process_vision_info
                
                images, videos = process_vision_info(messages_plain)
                processor_kwargs['images'] = images
                processor_kwargs['videos'] = videos
            
            if audio_paths:
                import librosa

                audios = []
                for path in audio_paths:
                    if path.startswith("file://"):
                        audios.append(librosa.load(path[len("file://") :], sr=self.processor.feature_extractor.sampling_rate)[0])
                    else:
                        audios.append(librosa.load(path, sr=self.processor.feature_extractor.sampling_rate)[0])
                processor_kwargs['audios'] = audios
            
            inputs = self.processor(**processor_kwargs, return_tensors="pt")

        for k, v in inputs.items():
            if torch.is_tensor(v):
                inputs[k] = v.to(self.hf_model.device)
        return inputs

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool,
        generate_cfg: dict,
    ) -> Iterator[List[Message]]:
        generate_cfg = copy.deepcopy(generate_cfg)
        inputs = self._get_inputs(messages)
        streamer = self._get_streamer()

        generate_cfg.update(inputs)
        generate_cfg.update(dict(
            streamer=streamer,
            max_new_tokens=generate_cfg.get('max_new_tokens', 2048)
        ))
        
        if 'seed' in generate_cfg:
            from transformers import set_seed
            set_seed(generate_cfg['seed'])
            del generate_cfg['seed']

        def generate_and_signal_complete():
            self.hf_model.generate(**generate_cfg)

        t1 = Thread(target=generate_and_signal_complete)
        t1.start()
        partial_text = ''
        for new_text in streamer:
            partial_text += new_text
            if delta_stream:
                yield [Message(ASSISTANT, new_text)]
            else:
                yield [Message(ASSISTANT, partial_text)]

    def _chat_no_stream(
        self,
        messages: List[Message],
        generate_cfg: dict,
    ) -> List[Message]:
        generate_cfg = copy.deepcopy(generate_cfg)

        inputs = self._get_inputs(messages)
        generate_cfg.update(inputs)
        generate_cfg.update(dict(
            max_new_tokens=generate_cfg.get('max_new_tokens', 2048)
        ))
        
        if 'seed' in generate_cfg:
            from transformers import set_seed
            set_seed(generate_cfg['seed'])
            del generate_cfg['seed']

        response = self.hf_model.generate(**generate_cfg)
        response = response[:, inputs['input_ids'].size(-1):]
        answer = self.tokenizer.batch_decode(response, skip_special_tokens=True)[0]
        return [Message(ASSISTANT, answer)]
