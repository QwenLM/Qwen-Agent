from abc import ABC, abstractmethod
from typing import Iterator, Union

from qwen_agent.llm.base import BaseChatModel

# TODO: Should *planning* just be another action that uses other actions?


class Action(ABC):

    def __init__(self, llm: BaseChatModel = None, stream: bool = False):
        self.llm = llm
        self.stream = stream

    @abstractmethod
    def run(self, *args, **kwargs) -> Union[str, Iterator[str]]:
        raise NotImplementedError

    # It is okay for an Action to not call LLMs.
    def _call_llm(self, prompt) -> Union[str, Iterator[str]]:
        return self.llm.chat(prompt=prompt, stream=self.stream)
