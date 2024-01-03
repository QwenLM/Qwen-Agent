import re

import json5

from qwen_agent import Agent
from qwen_agent.prompts import ExpandWriting, OutlineWriting, Summarize

default_plan = """{"action1": "summarize", "action2": "outline", "action3": "expand"}"""


def is_roman_numeral(s):
    pattern = r'^(I|V|X|L|C|D|M)+'
    match = re.match(pattern, s)
    return match is not None


class WriteFromScratch(Agent):

    def _run(self, user_request, ref_doc, lang: str = 'en'):
        # plan
        yield '\n========================= \n'
        yield '> Use Default plans: \n'
        yield default_plan
        res_plans = json5.loads(default_plan)

        summ = ''
        outline = ''
        for plan_id in sorted(res_plans.keys()):
            plan = res_plans[plan_id]
            if plan == 'summarize':
                yield '\n========================= \n'
                yield '> Summarize Browse Content: \n'
                summ = ''
                sum_agent = Summarize(llm=self.llm, stream=self.stream)
                res_sum = sum_agent.run(ref_doc=ref_doc, lang=lang)
                for trunk in res_sum:
                    summ += trunk
                    yield trunk
            elif plan == 'outline':
                yield '\n========================= \n'
                yield '> Generate Outline: \n'
                outline = ''
                otl_agent = OutlineWriting(llm=self.llm, stream=self.stream)
                res_otl = otl_agent.run(user_request=user_request,
                                        ref_doc=summ,
                                        lang=lang)
                for trunk in res_otl:
                    outline += trunk
                    yield trunk
            elif plan == 'expand':
                yield '\n========================= \n'
                yield '> Writing Text: \n'
                outline_list_all = outline.split('\n')
                outline_list = []
                for x in outline_list_all:
                    if is_roman_numeral(x):
                        outline_list.append(x)

                otl_num = len(outline_list)
                for i, v in enumerate(outline_list):
                    yield '\n# '
                    text = ''
                    index = i + 1
                    capture = v.strip()
                    capture_later = ''
                    if i < otl_num - 1:
                        capture_later = outline_list[i + 1].strip()
                    exp_agent = ExpandWriting(llm=self.llm, stream=self.stream)
                    res_exp = exp_agent.run(
                        user_request=user_request,
                        ref_doc=ref_doc,
                        outline=outline,
                        index=str(index),
                        capture=capture,
                        capture_later=capture_later,
                        lang=lang,
                    )
                    for trunk in res_exp:
                        text += trunk
                        yield trunk
            else:
                pass
