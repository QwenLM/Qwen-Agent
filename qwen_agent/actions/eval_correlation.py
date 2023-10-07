from qwen_agent.actions.base import Action

PROMPT_TEMPLATE_CN = """
判断下列续写内容中，谁和前置文本最相关
#前置文本：
{user_request}

#续写内容：
{content_list}

必须按照如下格式返回：
{{'best_id': '和前置文本最相关的续写内容的序号', 'reason': '原因'}}

"""

PROMPT_TEMPLATE_EN = """
Determine which of the following continuation text is most relevant to the previous text
# Previous text:
{user_request}

# Continuation text:
{content_list}

It must be returned in the following format:
{{'best_id ': 'the sequence number of the continuation text most relevant to the previous text', 'reason': 'the reason'}}

"""


class EvalCorr(Action):
    def __init__(self, llm=None, stream=False):
        super().__init__(llm=llm, stream=stream)

    def run(self, user_request, content_list, messages=None, prompt_lan='CN'):
        if prompt_lan == 'CN':
            prompt = PROMPT_TEMPLATE_CN.format(
                user_request=user_request,
                content_list=content_list
            )
        elif prompt_lan == 'EN':
            prompt = PROMPT_TEMPLATE_EN.format(
                user_request=user_request,
                content_list=content_list
            )
        return self._run(prompt, messages=messages)
