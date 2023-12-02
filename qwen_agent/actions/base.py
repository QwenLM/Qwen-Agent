from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.llm.base import BaseChatModel
from qwen_agent.utils.utils import has_chinese_chars

# TODO: Should *planning* just be another action that uses other actions?


class Action(ABC):

    def __init__(self, llm: BaseChatModel = None, stream: bool = False):
        self.llm = llm
        self.stream = stream

    def run(self, *args, **kwargs) -> Union[str, Iterator[str]]:
        if 'lang' not in kwargs:
            if has_chinese_chars([args, kwargs]):
                kwargs['lang'] = 'zh'
            else:
                kwargs['lang'] = 'en'
        return self._run(*args, **kwargs)

    @abstractmethod
    def _run(self, *args, **kwargs) -> Union[str, Iterator[str]]:
        raise NotImplementedError

    # It is okay for an Action to not call LLMs.
    def _call_llm(
        self,
        prompt: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        stop: Optional[List[str]] = None,
    ) -> Union[str, Iterator[str]]:
        return self.llm.chat(
            prompt=prompt,
            messages=messages,
            stop=stop,
            stream=self.stream,
        )
