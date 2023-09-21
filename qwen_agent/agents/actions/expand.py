from qwen_agent.agents.actions.base import Action

PROMPT_TEMPLATE_CN = """
你是一个写作助手，任务是依据参考资料，完成写作任务。
#参考资料：
{ref_doc}

写作标题是：{user_request}
大纲是：
{outline}

此时你的任务是扩写第{index}个一级标题对应的章节：{capture}。注意每个章节负责撰写不同的内容，所以你不需要为了全面而涵盖之后的内容。请不要在这里生成大纲。只依据给定的参考资料来写，不要引入其余知识。
"""

PROMPT_TEMPLATE_EN = """
You are a writing assistant. Your task is to complete writing article based on reference materials.

# References:
{ref_doc}

The title is: {user_request}

The outline is:
{outline}

At this point, your task is to expand the chapter corresponding to the {index} first level title: {capture}.
Note that each chapter is responsible for writing different content, so you don't need to cover the following content. Please do not generate an outline here. Write only based on the given reference materials and do not introduce other knowledge.
"""


class Expand(Action):

    def __init__(self, llm=None, stream=False):
        super().__init__(llm=llm, stream=stream)

    def run(self, ref_doc, user_request, outline='', index='1', capture='', capture_later='', messages=None, prompt_lan='CN'):
        if prompt_lan == 'CN':
            prompt = PROMPT_TEMPLATE_CN.format(
                ref_doc=ref_doc,
                user_request=user_request,
                index=index,
                outline=outline,
                capture=capture
            )
            if capture_later:
                prompt = prompt + '请在涉及 '+capture_later+' 时停止。'
        elif prompt_lan == 'EN':
            prompt = PROMPT_TEMPLATE_EN.format(
                ref_doc=ref_doc,
                user_request=user_request,
                index=index,
                outline=outline,
                capture=capture
            )
            if capture_later:
                prompt = prompt + ' Please stop when writing '+capture_later

        return self._run(prompt, messages=messages)
