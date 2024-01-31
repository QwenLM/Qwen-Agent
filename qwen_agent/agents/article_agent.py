import json
from typing import Dict, Iterator, List, Union

from qwen_agent.agents.assistant import Assistant
from qwen_agent.llm.schema import ASSISTANT, CONTENT, ROLE
from qwen_agent.prompts import ContinueWriting, WriteFromScratch


class ArticleAgent(Assistant):

    def _run(self,
             messages: List[Dict],
             lang: str = 'en',
             max_ref_token: int = 4000,
             full_article: bool = False,
             **kwargs) -> Union[str, Iterator[str]]:

        # need to use Memory agent for data management
        *_, last = self.mem.run(messages=messages,
                                max_ref_token=max_ref_token,
                                **kwargs)
        _ref = '\n\n'.join(
            json.dumps(x, ensure_ascii=False) for x in last[-1][CONTENT])

        response = []
        if _ref:
            response.append({
                ROLE:
                ASSISTANT,
                CONTENT:
                f'\n========================= \n> Search for relevant information: \n{_ref}\n'
            })
            yield response

        if full_article:
            writing_agent = WriteFromScratch(llm=self.llm)
        else:
            writing_agent = ContinueWriting(llm=self.llm)
            response.append({
                ROLE:
                ASSISTANT,
                CONTENT:
                '\n========================= \n> Writing Text: \n'
            })
            yield response
        res = writing_agent.run(messages=messages, lang=lang, knowledge=_ref)
        for trunk in res:
            yield response + trunk
