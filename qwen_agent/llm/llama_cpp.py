import copy
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.llm.base import register_llm
from qwen_agent.llm.function_calling import BaseFnCallModel
from qwen_agent.llm.schema import ASSISTANT, Message
from qwen_agent.log import logger

try:
    from llama_cpp import Llama
except ImportError as e:
    raise ImportError(
        "llama-cpp-python is required to use the llama_cpp backend.\n"
        "Install it with: pip install llama-cpp-python\n"
        "(add --extra-index-url for GPU/metal/...)") from e


@register_llm('llama_cpp')
class LlamaCpp(BaseFnCallModel):
    """
    llama.cpp backend (via llama-cpp-python bindings)

    Config example:

    llm_cfg = {
        'model_type': 'llama_cpp',
        'model_path': '/path/to/qwen2.5-7b-instruct-q5_k_m.gguf',
        # or (HuggingFace repo style)
        # 'repo_id': 'Qwen/Qwen2.5-7B-Instruct-GGUF',
        # 'filename': 'qwen2.5-7b-instruct-q5_k_m.gguf',
        'n_ctx': 8192,
        'n_gpu_layers': -1,           # -1 = all layers → GPU if possible
        'n_threads': 6,
        'temperature': 0.7,
        'max_tokens': 1024,
        'top_p': 0.9,
        'verbose': False,
    }
    """

    def __init__(self, cfg: Optional[Dict] = None):
        cfg = cfg or {}
        super().__init__(cfg)

        model_path = cfg.get('model_path')
        repo_id = cfg.get('repo_id')
        filename = cfg.get('filename')

        if not (model_path or (repo_id and filename)):
            raise ValueError(
                "llama_cpp backend requires either 'model_path' "
                "or both 'repo_id' and 'filename'"
            )

        llama_kwargs = {
            'n_ctx': cfg.get('n_ctx', 8192),
            'n_gpu_layers': cfg.get('n_gpu_layers', -1),
            'n_threads': cfg.get('n_threads'),
            'n_batch': cfg.get('n_batch', 512),
            'verbose': cfg.get('verbose', False),
        }

        if model_path:
            logger.info(f"Loading llama.cpp model from local path: {model_path}")
            self.llm = Llama(model_path=model_path, **llama_kwargs)
        else:
            logger.info(f"Downloading/Loading from HuggingFace: {repo_id} / {filename}")
            llama_kwargs['cache_dir'] = cfg.get('cache_dir')
            self.llm = Llama.from_pretrained(
                repo_id=repo_id,
                filename=filename,
                **llama_kwargs
            )

        self._supports_function_calling = True

    @property
    def support_multimodal_input(self) -> bool:
        return False

    @property
    def support_audio_input(self) -> bool:
        return False

    def _convert_messages(self, messages: List[Union[Message, Dict]]) -> List[Dict]:
        result = []

        for msg in messages:
            if isinstance(msg, Message):
                role = msg.role
                content = msg.content
            else:
                role = msg.get('role', 'user')
                content = msg.get('content', '')

            # Very basic content handling — extend later if needed
            if isinstance(content, str):
                text = content
            elif isinstance(content, (list, tuple)):
                parts = []
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        parts.append(item['text'])
                    else:
                        parts.append(str(item))
                text = ''.join(parts)
            else:
                text = str(content)

            result.append({'role': role, 'content': text})

        return result

    def _prepare_generate_kwargs(self, generate_cfg: Dict) -> Dict:
        cfg = copy.deepcopy(generate_cfg or {})
        return {
            'temperature': cfg.pop('temperature', 0.7),
            'top_p': cfg.pop('top_p', 0.9),
            'max_tokens': cfg.pop('max_tokens', cfg.pop('max_new_tokens', 1024)),
            'stop': cfg.pop('stop', None),
            **cfg,  # pass any extra llama.cpp sampling / generation flags
        }

    def _chat_stream(
            self,
            messages: List[Message],
            delta_stream: bool = False,
            generate_cfg: Optional[Dict] = None,
    ) -> Iterator[List[Message]]:
        llama_messages = self._convert_messages(messages)
        gen_kwargs = self._prepare_generate_kwargs(generate_cfg or {})

        accumulated = ""

        for chunk in self.llm.create_chat_completion(
                messages=llama_messages,
                stream=True,
                **gen_kwargs
        ):
            try:
                delta = chunk['choices'][0]['delta']
                content = delta.get('content', '')
            except (KeyError, IndexError, TypeError):
                content = ''

            if content:
                accumulated += content
                if delta_stream:
                    yield [Message(ASSISTANT, content)]
                else:
                    yield [Message(ASSISTANT, accumulated)]

    def _chat_no_stream(
            self,
            messages: List[Message],
            generate_cfg: Optional[Dict] = None,
    ) -> List[Message]:
        llama_messages = self._convert_messages(messages)
        gen_kwargs = self._prepare_generate_kwargs(generate_cfg or {})

        response = self.llm.create_chat_completion(
            messages=llama_messages,
            stream=False,
            **gen_kwargs
        )

        try:
            content = response['choices'][0]['message']['content']
        except (KeyError, IndexError):
            content = ''

        return [Message(ASSISTANT, content)]
