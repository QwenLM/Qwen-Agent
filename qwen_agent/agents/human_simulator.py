import json
import random
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.agents import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import Message
from qwen_agent.tools import BaseTool

STOP = '<|STOP|>'

DEFAULT_HUMAN_SIMULATOR_PROMPT = """"Play a game where you act as the human user and the user acts as the AI assistant.

# Rules:
- Ask questions and make requests as a typical human user would.
- Your questions should be related to the provided context or the chat history.
- You should output a JSON list of four possible questions, and nothing more.
- The questions must be diverse in their complexity, intentions, and language usage.
- If you feel the conversation can end, please output ["%s"] directly without any other content.""" % STOP


class HumanSimulator(Agent):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 **kwargs):
        if system_message:
            system_message = DEFAULT_HUMAN_SIMULATOR_PROMPT + '\n\n' + system_message
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description,
                         **kwargs)

    def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        if (not messages) or (messages[0].role != 'user'):
            begin_msg = 'Please role-play as a human user and make your first request.\n\nBegin!'
            messages = [Message(role='user', content=begin_msg)] + messages
        *_, respones = self._call_llm(messages=messages)
        rng = random.Random(kwargs.get('seed', 42))
        try:
            text = rng.choice(json.loads(respones[-1].content))
            if (not isinstance(text, str)) or (not text):
                text = STOP
            respones[-1].content = text
        except json.decoder.JSONDecodeError:
            respones[-1].content = STOP
        yield respones
