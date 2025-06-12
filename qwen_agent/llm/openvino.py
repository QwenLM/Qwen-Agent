# Copyright 2024 Intel Corporation. All rights reserved.
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
from typing import Dict, Iterator, List, Optional, Any
import queue
from threading import Event, Thread
import numpy as np
import openvino as ov
import openvino_genai

from qwen_agent.llm.base import register_llm
from qwen_agent.llm.function_calling import BaseFnCallModel
from qwen_agent.llm.schema import ASSISTANT, Message

@register_llm('openvino')
class OpenVINO(BaseFnCallModel):
    """
    OpenVINO Pipeline API.

    To use, you should have the 'optimum[openvino]' python package installed.

    Example export and quantize openvino model by command line:
        optimum-cli export openvino --model Qwen/Qwen2-7B-Instruct --task text-generation-with-past --weight-format int4 --group-size 128 --ratio 0.8 Qwen2-7B-Instruct-ov

    Example passing pipeline in directly:
        llm_cfg = {
            'ov_model_dir': 'Qwen2-7B-Instruct-ov',
            'model_type': 'openvino',
            'device': 'cpu'
            }
        system_instruction = '''After receiving the user's request, you should:
        - first draw an image and obtain the image url,
        - then run code `request.get(image_url)` to download the image,
        - and finally select an image operation from the given document to process the image.
        Please show the image using `plt.show()`.'''
        tools = ['my_image_gen', 'code_interpreter']
        files = ['./examples/resource/doc.pdf']
        bot = Assistant(llm=llm_cfg,
                system_message=system_instruction,
                function_list=tools,
                files=files)
    """

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        if 'ov_model_dir' not in cfg:
            raise ValueError('Please provide openvino model directory through `ov_model_dir` in cfg.')

        try:
            from optimum.intel.openvino import OVModelForCausalLM
        except ImportError as e:
            raise ImportError('Could not import optimum-intel python package for openvino. '
                              'Please install it with: '
                              "pip install -U 'optimum[openvino]'") from e
        try:
            from transformers import AutoConfig, AutoTokenizer
        except ImportError as e:
            raise ImportError('Could not import transformers python package for openvino. '
                              'Please install it with: '
                              "pip install -U 'transformers'") from e

        self.ov_model = OVModelForCausalLM.from_pretrained(
            cfg['ov_model_dir'],
            device=cfg.get('device', 'cpu'),
            ov_config=cfg.get('ov_config', {}),
            config=AutoConfig.from_pretrained(cfg['ov_model_dir']),
        )
        self.tokenizer = AutoTokenizer.from_pretrained(cfg['ov_model_dir'])

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool,
        generate_cfg: dict,
    ) -> Iterator[List[Message]]:
        from transformers import TextIteratorStreamer
        generate_cfg = copy.deepcopy(generate_cfg)
        messages_plain = [message.model_dump() for message in messages]
        input_token = self.tokenizer.apply_chat_template(messages_plain, add_generation_prompt=True, return_tensors='pt').to(self.ov_model.device)
        streamer = TextIteratorStreamer(self.tokenizer, timeout=60.0, skip_prompt=True, skip_special_tokens=True)
        generate_cfg.update(
            dict(
                input_ids=input_token,
                streamer=streamer,
                max_new_tokens=generate_cfg.get('max_new_tokens', 2048),
            ))
        del generate_cfg['seed']

        def generate_and_signal_complete():
            self.ov_model.generate(**generate_cfg)

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
        messages_plain = [message.model_dump() for message in messages]
        input_token = self.tokenizer.apply_chat_template(messages_plain, add_generation_prompt=True, return_tensors='pt').to(self.ov_model.device)
        generate_cfg.update(
            dict(
                input_ids=input_token,
                max_new_tokens=generate_cfg.get('max_new_tokens', 2048),
            ))
        del generate_cfg['seed']

        response = self.ov_model.generate(**generate_cfg)
        response = response[:, len(input_token[0]):]
        answer = self.tokenizer.batch_decode(response, skip_special_tokens=True)[0]
        return [Message(ASSISTANT, answer)]


@register_llm("openvino-genai")
class OpenVINOGenAI(BaseFnCallModel):
    """
    OpenVINO GenAI Pipeline API.

    To use, you should have the 'openvino-genai' python package installed.

    Example export and quantize openvino model by command line:
        optimum-cli export openvino --model Qwen/Qwen3-8B --task text-generation-with-past --weight-format int4 --group-size 128 --ratio 0.8 Qwen3-8B-ov

    Example passing pipeline in directly:
        llm_cfg = {
            'ov_model_dir': 'Qwen3-8B-ov',
            'model_type': 'openvino-genaiu',
            'device': 'CPU'
            }
        system_instruction = '''After receiving the user's request, you should:
        - first draw an image and obtain the image url,
        - then run code `request.get(image_url)` to download the image,
        - and finally select an image operation from the given document to process the image.
        Please show the image using `plt.show()`.'''
        tools = ['my_image_gen', 'code_interpreter']
        files = ['./examples/resource/doc.pdf']
        bot = Assistant(llm=llm_cfg,
                system_message=system_instruction,
                function_list=tools,
                files=files)
    """

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        if "ov_model_dir" not in cfg:
            raise ValueError(
                "Please provide openvino model directory through `ov_model_dir` in cfg."
            )

        self.pipe = openvino_genai.LLMPipeline(
            cfg["ov_model_dir"], device=cfg.get("device", "CPU")
        )
        self.config = openvino_genai.GenerationConfig()
        self.use_genai_tokenizer = cfg.get("use_genai_tokenizer", True)
        self.chat_mode = cfg.get("chat_mode", False)
        self.streamer = ChunkStreamer(self.tokenizer)
        self.full_prompt = True
        if self.chat_mode:
            self.pipe.start_chat()

        if self.use_genai_tokenizer:
            self.tokenizer = self.pipe.get_tokenizer()
            if "genai_chat_template" in cfg:
                self.tokenizer.set_chat_template(
                    cfg["genai_chat_template"],
                )
        else:
            try:
                from transformers import AutoTokenizer
            except ImportError as e:
                raise ImportError(
                    "Could not import transformers python package for openvino. "
                    "Please install it with: "
                    "pip install -U 'transformers'"
                ) from e
            self.tokenizer = AutoTokenizer.from_pretrained(cfg["ov_model_dir"])

        class IterableStreamer(openvino_genai.StreamerBase):
            """
            A custom streamer class for handling token streaming
            and detokenization with buffering.

            Attributes:
                tokenizer (Tokenizer): The tokenizer used for encoding
                and decoding tokens.
                tokens_cache (list): A buffer to accumulate tokens
                for detokenization.
                text_queue (Queue): A synchronized queue
                for storing decoded text chunks.
                print_len (int): The length of the printed text
                to manage incremental decoding.

            """

            def __init__(self, tokenizer: Any) -> None:
                """
                Initializes the IterableStreamer with the given tokenizer.

                Args:
                    tokenizer (Tokenizer): The tokenizer to use for encoding
                    and decoding tokens.

                """
                super().__init__()
                self.tokenizer = tokenizer
                self.tokens_cache: list[int] = []
                self.text_queue: Any = queue.Queue()
                self.print_len = 0

            def __iter__(self) -> self:
                """
                Returns the iterator object itself.
                """
                return self

            def __next__(self) -> str:
                """
                Returns the next value from the text queue.

                Returns:
                    str: The next decoded text chunk.

                Raises:
                    StopIteration: If there are no more elements in the queue.

                """
                value = (
                    self.text_queue.get()
                )  # get() will be blocked until a token is available.
                if value is None:
                    raise StopIteration
                return value

            def get_stop_flag(self) -> bool:
                """
                Checks whether the generation process should be stopped.

                Returns:
                    bool: Always returns False in this implementation.

                """
                return False

            def put_word(self, word: Any) -> None:
                """
                Puts a word into the text queue.

                Args:
                    word (str): The word to put into the queue.

                """
                self.text_queue.put(word)

            def put(self, token_id: int) -> bool:
                """
                Processes a token and manages the decoding buffer.
                Adds decoded text to the queue.

                Args:
                    token_id (int): The token_id to process.

                Returns:
                    bool: True if generation should be stopped, False otherwise.

                """
                self.tokens_cache.append(token_id)
                text = self.tokenizer.decode(
                    self.tokens_cache, skip_special_tokens=True
                )

                word = ""
                if len(text) > self.print_len and text[-1] == "\n":
                    word = text[self.print_len :]
                    self.tokens_cache = []
                    self.print_len = 0
                elif len(text) >= 3 and text[-3:] == chr(65533):
                    pass
                elif len(text) > self.print_len:
                    word = text[self.print_len :]
                    self.print_len = len(text)
                self.put_word(word)

                if self.get_stop_flag():
                    self.end()
                    return True
                else:
                    return False

            def end(self) -> None:
                """
                Flushes residual tokens from the buffer
                and puts a None value in the queue to signal the end.
                """
                text = self.tokenizer.decode(
                    self.tokens_cache, skip_special_tokens=True
                )
                if len(text) > self.print_len:
                    word = text[self.print_len :]
                    self.put_word(word)
                    self.tokens_cache = []
                    self.print_len = 0
                self.put_word(None)

            def reset(self) -> None:
                """
                Resets the state.
                """
                self.tokens_cache = []
                self.text_queue = queue.Queue()
                self.print_len = 0

        class ChunkStreamer(IterableStreamer):
            def __init__(self, tokenizer: Any, tokens_len: int = 4) -> None:
                super().__init__(tokenizer)
                self.tokens_len = tokens_len

            def put(self, token_id: int) -> bool:
                if (len(self.tokens_cache) + 1) % self.tokens_len != 0:
                    self.tokens_cache.append(token_id)
                    return False
                return super().put(token_id)

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool,
        generate_cfg: dict,
    ) -> Iterator[List[Message]]:
        generate_cfg = copy.deepcopy(generate_cfg)

        self.config.max_new_tokens = generate_cfg.get("max_new_tokens", self.config.max_new_tokens)
        self.config.do_sample = generate_cfg.get("do_sample", self.config.do_sample)
        self.config.top_p = generate_cfg.get("top_p", self.config.top_p)
        self.config.top_k = generate_cfg.get("top_k", self.config.top_k)
        self.config.temperature = generate_cfg.get("temperature", self.config.temperature)

        if self.full_prompt:
            messages_plain = [message.model_dump() for message in messages]
        else:
            messages_plain = [messages[-1].model_dump()]

        if self.use_genai_tokenizer:
            inputs_ov = self.tokenizer.apply_chat_template(
                messages_plain, add_generation_prompt=True
            ) 
        else:
            chat_prompt = self.tokenizer.apply_chat_template(
                messages_plain, tokenize=False, add_generation_prompt=True
            )
            tokenized = self.tokenizer(
                chat_prompt, return_tensors="pt", add_special_tokens=False
            )

            input_ids = np.array([tokenized["input_ids"][0]], dtype=np.int64)
            attention_mask = np.array([tokenized["attention_mask"][0]], dtype=np.int64)
            inputs_ov = openvino_genai.TokenizedInputs(
                ov.Tensor(input_ids), ov.Tensor(attention_mask)
            )

        stream_complete = Event()

        def generate_and_signal_complete() -> None:
            """
            Generation function for single thread.
            """
            self.streamer.reset()
            self.pipe.generate(
                inputs_ov,
                streamer=self.streamer,
                generation_config=self.config,
            )
            stream_complete.set()
            self.streamer.end()

        t1 = Thread(target=generate_and_signal_complete)
        t1.start()
        if self.chat_mode:
            self.full_prompt = False

        partial_text = ""
        for new_text in self.streamer:
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

        if self.full_prompt:
            messages_plain = [message.model_dump() for message in messages]
        else:
            messages_plain = [messages[-1].model_dump()]

        self.config.max_new_tokens = generate_cfg.get("max_new_tokens", self.config.max_new_tokens)
        self.config.do_sample = generate_cfg.get("do_sample", self.config.do_sample)
        self.config.top_p = generate_cfg.get("top_p", self.config.top_p)
        self.config.top_k = generate_cfg.get("top_k", self.config.top_k)
        self.config.temperature = generate_cfg.get("temperature", self.config.temperature)

        messages_plain = [message.model_dump() for message in messages]
        if self.use_genai_tokenizer:
            inputs_ov = self.tokenizer.apply_chat_template(
                messages_plain, add_generation_prompt=True
            )
            answer_ov = self.pipe.generate(
                inputs_ov, generation_config=self.config,
            )
        else:
            chat_prompt = self.tokenizer.apply_chat_template(
                messages_plain, tokenize=False, add_generation_prompt=True
            )
            tokenized = self.tokenizer(
                chat_prompt, return_tensors="pt", add_special_tokens=False
            )

            input_ids = np.array([tokenized["input_ids"][0]], dtype=np.int64)
            attention_mask = np.array([tokenized["attention_mask"][0]], dtype=np.int64)
            inputs_ov = openvino_genai.TokenizedInputs(
                ov.Tensor(input_ids), ov.Tensor(attention_mask)
            )
            result_ov = self.pipe.generate(
                inputs_ov, generation_config=self.config,
            ).tokens[0]
            answer_ov = self.tokenizer.decode(result_ov, skip_special_tokens=True)
        if self.chat_mode:
            self.full_prompt = False
        return [Message(ASSISTANT, answer_ov)]
