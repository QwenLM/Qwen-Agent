"""
固定整体流程：
 Step1: Similarity Search: 从参考资料中检索相关部分（段落）

 Step2: outline
 Step3: expand
    - 每expand一章节, 触发决策是否调用plugin(画图, code interpreter, 运行代码, browser)

Note: Step2&3 也可以planning, 暂时固定
"""
import json
import re

from qwen_agent.agents.actions import Expand, Outline, Plugin, Simple
from qwen_agent.agents.actions.actions import get_action_list
from qwen_agent.agents.planning.plan import Plan, default_plan

from qwen_agent.agents.tools.tools import tools_list  # NOQA

PROMPT_REACT_CUSTOM_EN = """Answer the following questions as best you can. You have access to the following tools:

{tools_text}

Rules for using tools:
If the question includes code, you can consider selecting relevant tools to run the code.
If the question is to describe a series of data, consider analyzing the data and drawing a graph.
If the question is to introduce a well-known entity, such as Spider Man, the Forbidden City, etc., you can consider drawing a related diagram.
...

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tools_name_text}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question. If you do not use tools, please end the generation directly without answering the Final Answer...


Begin!

Question: {query}"""

PROMPT_REACT_CUSTOM_CN = """给你一段文本，你需要分析文本，并按照选择工具的规则选择合适的工具来生成想要的结果。

可用的工具:

{tools_text}

选择工具的规则:

如果文本中包含Python代码，可以考虑选择 代码解释器 工具运行输入文本中的代码
如果文本是描述一系列数据，可以考虑选择 代码解释器 工具分析数据并生成代码画图
如果文本是介绍一个有名的实体，例如蜘蛛侠、故宫等，可以考虑画一幅相关的图
......

使用如下模板:

Text: the input text
Thought: you should always think about what to do
Action: the action to take, should be one of [{tools_name_text}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Final Answer: the final answer to the original input text. 如果不使用工具，请直接结束生成，不需要生成Final Answer。


Begin!

Text: {query}"""


def is_roman_numeral(s):
    pattern = r'^(I|V|X|L|C|D|M)+'
    match = re.match(pattern, s)
    return match is not None


class WriteFromZero:
    def __init__(self, llm=None, task='ghostwriter', stream=False, auto_agent=False):
        self.llm = llm
        self.stream = stream
        self.task = task
        self.auto_agent = auto_agent

    def run(self, ref_doc, user_request, open_write_plan=False, messages=None, prompt_lan='CN'):
        action_list = get_action_list(self.task)
        # plan
        if open_write_plan:
            agent_plan = Plan(llm=self.llm, stream=self.stream)
            plans = agent_plan.run(ref_doc, user_request, action_list)
            yield '\n========================= \n'
            yield '> Plans: \n'
            res_plans = ''
            for trunk in plans:
                res_plans += trunk
                yield trunk
            try:
                res_plans = json.loads(res_plans.split('Plan:')[-1].strip())
            except Exception as ex:
                print(ex)
                yield '\n========================= \n'
                yield '> Use Default plans: \n'
                yield default_plan
                res_plans = json.loads(default_plan)
        else:
            yield '\n========================= \n'
            yield '> Use Default plans: \n'
            yield default_plan
            res_plans = json.loads(default_plan)

        # 依次执行plan
        summ = ''
        outline = ''
        for plan_id, plan in res_plans.items():
            if plan == 'summarize':
                yield '\n========================= \n'
                yield '> Summarize Browse Content: \n'
                summ = ''
                sum_agent = Simple(llm=self.llm, stream=self.stream)
                if prompt_lan == 'CN':
                    res_sum = sum_agent.run(ref_doc, '总结参考资料的主要内容')
                elif prompt_lan == 'EN':
                    res_sum = sum_agent.run(ref_doc, 'Summarize the main content of reference materials.')
                for trunk in res_sum:
                    summ += trunk
                    yield trunk
            elif plan == 'outline':
                yield '\n========================= \n'
                yield '> Generate Outline: \n'
                outline = ''
                otl_agent = Outline(llm=self.llm, stream=self.stream)
                res_otl = otl_agent.run(summ, user_request)
                for trunk in res_otl:
                    outline += trunk
                    yield trunk
            elif plan == 'expand':
                yield '\n========================= \n'
                yield '> Writing Text: \n'
                outline_list_all = outline.split('\n')  # 只提取一级标题涉及的行
                outline_list = []
                for x in outline_list_all:
                    if is_roman_numeral(x):
                        outline_list.append(x)

                if self.auto_agent:
                    if prompt_lan == 'CN':
                        plug_agent = Plugin(llm=self.llm, stream=False, list_of_plugin_info=tools_list, prompt=PROMPT_REACT_CUSTOM_CN)
                    elif prompt_lan == 'EN':
                        plug_agent = Plugin(llm=self.llm, stream=False, list_of_plugin_info=tools_list, prompt=PROMPT_REACT_CUSTOM_EN)
                otl_num = len(outline_list)
                for i, v in enumerate(outline_list):
                    yield '\n# '
                    text = ''
                    index = i+1
                    capture = v.strip()
                    capture_later = ''
                    if i < otl_num-1:
                        capture_later = outline_list[i+1].strip()
                    exp_agent = Expand(llm=self.llm, stream=self.stream)
                    res_exp = exp_agent.run(ref_doc, user_request, outline=outline, index=str(index), capture=capture, capture_later=capture_later)
                    for trunk in res_exp:
                        text += trunk
                        yield trunk
                    if self.auto_agent:
                        yield '\n> In selecting plugins...\n'
                        res_plug = plug_agent.run(text)
                        if not plug_agent.stream and 'Action:' not in res_plug:
                            yield '\n> No plugins required\n'
                            continue
                        else:
                            for trunk in res_plug:
                                yield trunk
            else:
                pass
