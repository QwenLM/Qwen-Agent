import re
from typing import Iterator, List

import json5

from qwen_agent import Agent
from qwen_agent.agents.assistant import Assistant
from qwen_agent.agents.writing import ExpandWriting, OutlineWriting
from qwen_agent.llm.schema import ASSISTANT, CONTENT, USER, Message

default_plan = """{"action1": "summarize", "action2": "outline", "action3": "expand"}"""


def is_roman_numeral(s):
    pattern = r'^(I|V|X|L|C|D|M)+'
    match = re.match(pattern, s)
    return match is not None


class WriteFromScratch(Agent):

    def _run(self, messages: List[Message], knowledge: str = '', lang: str = 'en') -> Iterator[List[Message]]:

        response = [Message(ASSISTANT, f'>\n> Use Default plans: \n{default_plan}')]
        yield response
        res_plans = json5.loads(default_plan)

        summ = ''
        outline = ''
        for plan_id in sorted(res_plans.keys()):
            plan = res_plans[plan_id]
            if plan == 'summarize':
                response.append(Message(ASSISTANT, '>\n> Summarize Browse Content: \n'))
                yield response

                if lang == 'zh':
                    user_request = '总结参考资料的主要内容'
                elif lang == 'en':
                    user_request = 'Summarize the main content of reference materials.'
                else:
                    raise NotImplementedError
                sum_agent = Assistant(llm=self.llm)
                res_sum = sum_agent.run(messages=[Message(USER, user_request)], knowledge=knowledge, lang=lang)
                chunk = None
                for chunk in res_sum:
                    yield response + chunk
                if chunk:
                    response.extend(chunk)
                    summ = chunk[-1][CONTENT]
            elif plan == 'outline':
                response.append(Message(ASSISTANT, '>\n> Generate Outline: \n'))
                yield response

                otl_agent = OutlineWriting(llm=self.llm)
                res_otl = otl_agent.run(messages=messages, knowledge=summ, lang=lang)
                chunk = None
                for chunk in res_otl:
                    yield response + chunk
                if chunk:
                    response.extend(chunk)
                    outline = chunk[-1][CONTENT]
            elif plan == 'expand':
                response.append(Message(ASSISTANT, '>\n> Writing Text: \n'))
                yield response

                outline_list_all = outline.split('\n')
                outline_list = []
                for x in outline_list_all:
                    if is_roman_numeral(x):
                        outline_list.append(x)

                otl_num = len(outline_list)
                for i, v in enumerate(outline_list):
                    response.append(Message(ASSISTANT, '>\n# '))
                    yield response

                    index = i + 1
                    capture = v.strip()
                    capture_later = ''
                    if i < otl_num - 1:
                        capture_later = outline_list[i + 1].strip()
                    exp_agent = ExpandWriting(llm=self.llm)
                    res_exp = exp_agent.run(
                        messages=messages,
                        knowledge=knowledge,
                        outline=outline,
                        index=str(index),
                        capture=capture,
                        capture_later=capture_later,
                        lang=lang,
                    )
                    chunk = None
                    for chunk in res_exp:
                        yield response + chunk
                    if chunk:
                        response.extend(chunk)
            else:
                pass
