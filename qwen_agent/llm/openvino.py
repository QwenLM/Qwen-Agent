from typing import Dict, Iterator, List, Optional
from threading import Thread

from optimum.intel.openvino import OVModelForCausalLM
from transformers import (AutoTokenizer, AutoConfig,
                          TextIteratorStreamer, StoppingCriteriaList, StoppingCriteria)

from qwen_agent.llm.base import register_llm
from qwen_agent.llm.schema import ASSISTANT, DEFAULT_SYSTEM_MESSAGE, SYSTEM, USER, Message
from qwen_agent.llm.text_base import BaseTextChatModel
from qwen_agent.log import logger


from transformers.generation.stopping_criteria import StoppingCriteriaList, StoppingCriteria


class StopSequenceCriteria(StoppingCriteria):
    """
    This class can be used to stop generation whenever a sequence of tokens is encountered.

    Args:
        stop_sequences (`str` or `List[str]`):
            The sequence (or list of sequences) on which to stop execution.
        tokenizer:
            The tokenizer used to decode the model outputs.
    """

    def __init__(self, stop_sequences, tokenizer):
        if isinstance(stop_sequences, str):
            stop_sequences = [stop_sequences]
        self.stop_sequences = stop_sequences
        self.tokenizer = tokenizer

    def __call__(self, input_ids, scores, **kwargs) -> bool:
        decoded_output = self.tokenizer.decode(input_ids.tolist()[0])
        return any(decoded_output.endswith(stop_sequence) for stop_sequence in self.stop_sequences)


@register_llm('openvino')
class OpenVINO(BaseTextChatModel):
    """OpenVINO Pipeline API.

    To use, you should have the ``optimum[openvino,nncf]`` python package installed.

    Example export and quantizie from_model_id by command line:
        optimum-cli export openvino --model Qwen/Qwen2-7B-Instruct --task text-generation-with-past --weight-format int4 --group-size 128 --ratio 0.8 Qwen2-7B-Instruct-ov
    
    Example passing pipeline in directly:
        llm_cfg = {
            'ov_model_dir': 'Qwen2-7B-Instruct-ov',
            'model_type': 'openvino'
            }
        system_instruction = '''You are a helpful assistant.
        After receiving the user's request, you should:
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
            raise ValueError(
                f'Please provide openvino model directory through `ov_model_dir` in cfg')

        self.ov_model = OVModelForCausalLM.from_pretrained(
            cfg['ov_model_dir'],
            device=cfg.get('device', 'cpu'),
            ov_config=cfg.get('ov_config', {}),
            config=AutoConfig.from_pretrained(cfg['ov_model_dir']),
        )
        self.tokenizer = AutoTokenizer.from_pretrained(cfg["ov_model_dir"])

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool,
        generate_cfg: dict,
    ) -> Iterator[List[Message]]:

        prompt = self._build_text_completion_prompt(messages)
        logger.debug(f'*{prompt}*')
        input_token = self.tokenizer(prompt, return_tensors="pt").input_ids
        streamer = TextIteratorStreamer(
            self.tokenizer, timeout=60.0, skip_prompt=True, skip_special_tokens=True)
        generate_cfg.update(dict(
            input_ids=input_token,
            streamer=streamer,
            max_new_tokens=generate_cfg.get('max_new_tokens', 1024),
            stopping_criteria=StoppingCriteriaList(
                [StopSequenceCriteria(generate_cfg['stop'], self.tokenizer)])
        ))
        del generate_cfg['stop']

        def generate_and_signal_complete():
            self.ov_model.generate(**generate_cfg)
        t1 = Thread(target=generate_and_signal_complete)
        t1.start()
        partial_text = ""
        for new_text in streamer:
            partial_text += new_text
            yield [Message(ASSISTANT, partial_text)]

    def _chat_no_stream(
        self,
        messages: List[Message],
        generate_cfg: dict,
    ) -> List[Message]:
        prompt = self._build_text_completion_prompt(messages)
        logger.debug(f'*{prompt}*')
        input_token = self.tokenizer(prompt, return_tensors="pt").input_ids
        generate_cfg.update(dict(
            input_ids=input_token,
            max_new_tokens=generate_cfg.get('max_new_tokens', 1024),
            stopping_criteria=StoppingCriteriaList(
                [StopSequenceCriteria(generate_cfg['stop'], self.tokenizer)])
        ))
        del generate_cfg['stop']
        response = self.ov_model.generate(**generate_cfg)
        response = response[:, len(input_token[0]):]
        answer = self.tokenizer.batch_decode(
            response, skip_special_tokens=True)[0]
        return [Message(ASSISTANT, answer)]

    @staticmethod
    def _build_text_completion_prompt(messages: List[Message]) -> str:
        im_start = '<|im_start|>'
        im_end = '<|im_end|>'
        if messages[0].role == SYSTEM:
            sys = messages[0].content
            assert isinstance(sys, str)
            prompt = f'{im_start}{SYSTEM}\n{sys}{im_end}'
        else:
            prompt = f'{im_start}{SYSTEM}\n{DEFAULT_SYSTEM_MESSAGE}{im_end}'
        if messages[-1].role != ASSISTANT:
            messages.append(Message(ASSISTANT, ''))
        for msg in messages:
            assert isinstance(msg.content, str)
            if msg.role == USER:
                query = msg.content.lstrip('\n').rstrip()
                prompt += f'\n{im_start}{USER}\n{query}{im_end}'
            elif msg.role == ASSISTANT:
                response = msg.content.lstrip('\n').rstrip()
                prompt += f'\n{im_start}{ASSISTANT}\n{response}{im_end}'
        assert prompt.endswith(im_end)
        prompt = prompt[:-len(im_end)]
        return prompt
