from abc import abstractmethod
from typing import Dict, Iterator, List, Optional


class LLMBase:
    def __init__(self, model='qwen', api_key='',):

        self.model = model
        self.memory = None
        self.api_key = api_key.strip()

    def chat(self, query: str, stream: bool = False, messages: List[Dict] = None, stop: Optional[List[str]] = None):
        if stream:
            return self._chat_stream(query, messages, stop=stop)
        else:
            return self._chat_no_stream(query, messages, stop=stop)

    @abstractmethod
    def _chat_stream(self, query: str, messages=None, stop=None) -> Iterator[str]:
        raise NotImplementedError

    @abstractmethod
    def _chat_no_stream(self, query, messages=None, stop=None) -> str:
        raise NotImplementedError
