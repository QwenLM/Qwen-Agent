from qwen_agent.llm.qwen import qwen_chat, qwen_chat_no_stream

PROMPT_TEMPLATE = """
你是一个写作助手，擅长阅读参考资料，来完成用户需求。
#参考资料：
{ref_doc}

下面是动作选项列表，可以选择有助于完成用户需求的一个或多个动作：
#动作列表
{action_list}

请依据参考资料，制定计划完成用户需求，按照如下格式返回：
Question: 用户需求。
Thought: 生成计划的原因。
Plan: 生成的计划。以JSON格式返回，例如{"action1": action_name of the first action, "action2": action_name of the second action}

举例：
#Example1：
Question: 主题在讲什么？
Thought: 该需求可以直接回答
Plan: {"action1": summarize}

#Example2:
Question: 写一篇预言TFBOYS解散的稿子
Thought: 为了实现该需求，需要先总结参考资料，列出稿子大纲，扩写稿子
Plan: {"action1": summarize, "action3": outline, "action4": expand}

Question：{user_request}
"""

default_plan = """{"action1": "summarize", "action2": "outline", "action3": "expand"}"""


class Plan:
    def __init__(self, llm=None, stream=False):
        self.llm = llm
        self.stream = stream

    def run(self, ref_doc, user_request, action_list, messages=None):
        prompt = PROMPT_TEMPLATE.format(
            ref_doc=ref_doc,
            user_request=user_request,
            action_list=action_list,
        )
        if self.llm:
            return self.llm.chat(prompt, messages=messages, stream=self.stream)
        elif self.stream:
            return qwen_chat(prompt)
        else:
            return qwen_chat_no_stream(prompt)
