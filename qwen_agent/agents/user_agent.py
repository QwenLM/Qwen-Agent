from typing import Iterator, List

from qwen_agent.agent import Agent
from qwen_agent.llm.schema import Message

PENDING_USER_INPUT = '<!-- INTERRUPT: PENDING_USER_INPUT -->'


class UserAgent(Agent):

    def _run(self, messages: List[Message], **kwargs) -> Iterator[List[Message]]:
        yield [Message(role='user', content=PENDING_USER_INPUT, name=self.name)]
