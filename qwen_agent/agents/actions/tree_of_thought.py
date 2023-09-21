"""
ToT:    From the initial state to the final goal, there are n rounds of generation in between, with each round recorded as
        one thought, and n thoughts form the final path
Step1:  Generate k thoughts
Step2:  Evaluate whether the thoughts are beneficial for achieving goals, only choose positive thoughts
"""
import json

from qwen_agent.agents.actions import ContinueWriting, EvalCorr
from qwen_agent.utils.util import get_last_one_line_context


class ToT:
    def __init__(self, llm=None, steps=1, choices=3):
        self.llm = llm
        self.steps = steps
        self.choices = choices

    def run(self, ref_doc, user_request):
        for step in range(self.steps):
            # Generate
            chois = []
            choices = []
            yield '\n========================= \n'
            yield '> 生成选项：\n'
            for i in range(self.choices):
                tmp = ''
                id_tmp = str(i+1)+': '
                yield str(i+1)+': '
                agent = ContinueWriting(self.llm, stream=True)
                res = agent.run(ref_doc, user_request)

                for trunk in res:
                    tmp += trunk
                    id_tmp += trunk
                    yield trunk
                id_tmp += '\n'
                yield '\n'
                chois.append(tmp)
                choices.append(id_tmp)
            # print(choices)

            # Eval
            yield '\n========================= \n'
            yield '> 评估：\n'
            up_context = get_last_one_line_context(user_request)
            agent = EvalCorr(self.llm, stream=True)
            res = agent.run(up_context, choices)
            tmp = ''
            for trunk in res:
                tmp += trunk
                yield trunk
            res = tmp
            # print(res)

        try:
            res = json.loads(res)
            choi = chois[int(res['best_id'])-1]
            yield '\n========================= \n'
            yield '> Final Answer: '+choi
            # return choi
        except Exception as ex:
            print('Error: ', ex)
            yield '\n========================= \n'
            yield '> Final Answer: '+chois[0]
            # return chois[0]
