from typing import Dict, List, Optional

import jsonlines

from qwen_agent import Agent
from qwen_agent.utils.utils import build_raw_prompt

TOOL_TEMPLATE_ZH = """# 工具

## 你拥有如下工具：

{tool_descs}

## 你可以在回复中插入零次、一次或多次以下命令以调用工具：

✿FUNCTION✿: 工具名称，必须是[{tool_names}]之一
✿ARGS✿: 工具输入
✿RESULT✿: 工具结果
✿RETURN✿: 根据工具结果进行回复，如果存在url，请使用如何格式展示出来：![图片](url)

"""

PROMPT_TEMPLATE_ZH = """
# 指令

{role_prompt}

明白了请说“好的。”，不要说其他的。
"""

KNOWLEDGE_TEMPLATE_ZH = """

# 知识库

{ref_doc}

"""

KNOWLEDGE_TEMPLATE_EN = """

# Knowledge Base

{ref_doc}

"""

TOOL_TEMPLATE_EN = """# Tools

## You have access to the following tools:

{tool_descs}

## When you need to call a tool, please insert the following command in your reply, which can be called zero or multiple times according to your needs:

✿FUNCTION✿: The tool to use, should be one of [{tool_names}]
✿ARGS✿: The input of the tool, need to be formatted as a JSON
✿RESULT✿: The result returned by the tool
✿RETURN✿: Summarize the results based on the ✿RESULT✿

"""

PROMPT_TEMPLATE_EN = """
#Instructions

{role_prompt}


If you understand, please say 'Okay.' Don't say anything else.
"""

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}

KNOWLEDGE_TEMPLATE = {'zh': KNOWLEDGE_TEMPLATE_ZH, 'en': KNOWLEDGE_TEMPLATE_EN}

TOOL_TEMPLATE = {
    'zh': TOOL_TEMPLATE_ZH,
    'en': TOOL_TEMPLATE_EN,
}

SYSTEM_ANSWER_TEMPLATE = {
    'zh': '好的。',
    'en': 'Okay.',
}

SPECIAL_PREFIX_TEMPLATE = {
    'zh': '(你可以使用工具：[{tool_names}])',
    'en': '(You have access to tools: [{tool_names}])',
}

ACTION_TOKEN = '\n✿FUNCTION✿:'
ARGS_TOKEN = '\n✿ARGS✿:'
OBSERVATION_TOKEN = '\n✿RESULT✿:'
ANSWER_TOKEN = '\n✿RETURN✿:'


class RolePlay(Agent):

    def _run(self,
             user_request,
             response_to_continue: str = None,
             role_prompt: str = None,
             functions: Optional[dict] = None,
             history: Optional[List[Dict]] = None,
             ref_doc: str = None,
             lang: str = 'zh'):
        self.functions = functions or {}
        self.role_prompt = role_prompt

        self.tool_descs = '\n\n'.join(tool.function_plain_text
                                      for tool in functions.values())
        self.tool_names = ','.join(tool.name for tool in functions.values())

        self.system_prompt = ''
        self.query_prefix = ''
        if ref_doc:
            self.system_prompt += KNOWLEDGE_TEMPLATE[lang].format(
                ref_doc=ref_doc)
        if self.functions:
            self.system_prompt += TOOL_TEMPLATE[lang].format(
                tool_descs=self.tool_descs, tool_names=self.tool_names)
            self.query_prefix = SPECIAL_PREFIX_TEMPLATE[lang].format(
                tool_names=self.tool_names)
        self.system_prompt += PROMPT_TEMPLATE[lang].format(
            role_prompt=self.role_prompt)

        # Concat the system as one round of dialogue
        messages = ([{
            'role': 'user',
            'content': self.system_prompt
        }, {
            'role': 'assistant',
            'content': SYSTEM_ANSWER_TEMPLATE[lang]
        }])

        # Limit the length of conversation history
        if history:
            for x in history:
                messages.append({
                    'role': 'user',
                    'content': x[0],
                })
                messages.append({
                    'role': 'assistant',
                    'content': x[1],
                })

        # concat the new messages
        messages.append({
            'role': 'user',
            'content': self.query_prefix + user_request
        })
        messages.append({'role': 'assistant', 'content': ''})

        with jsonlines.open('log.jsonl', mode='a') as writer:
            writer.write(messages)

        planning_prompt = build_raw_prompt(messages)
        if response_to_continue:
            planning_prompt += response_to_continue

        max_turn = 5
        while True and max_turn > 0:
            max_turn -= 1
            output = self.llm.chat_with_raw_prompt(
                prompt=planning_prompt,
                stop=['✿RESULT✿:', '✿RESULT✿:\n'],
            )
            use_tool, action, action_input, output = self._detect_tool(output)

            yield output
            if use_tool:
                observation = self._call_tool(action, action_input)
                observation = f'\n✿RESULT✿: {observation}\n✿RETURN✿:'
                yield observation
                planning_prompt += output + observation
            else:
                planning_prompt += output
                break

    def _detect_tool_by_special_token(self, text: str):
        func_name, func_args = None, None
        i = text.rfind(ACTION_TOKEN)
        j = text.rfind(ARGS_TOKEN)
        k = text.rfind(OBSERVATION_TOKEN)
        if 0 <= i < j:  # If the text has `Action` and `Action input`,
            if k < j:  # but does not contain `✿RESULT✿`,
                # then it is likely that `✿RESULT✿` is ommited by the LLM,
                # because the output text may have discarded the stop word.
                text = text.rstrip() + OBSERVATION_TOKEN  # Add it back.
            k = text.rfind(OBSERVATION_TOKEN)
            func_name = text[i + len(ACTION_TOKEN):j].strip()
            func_args = text[j + len(ARGS_TOKEN):k].strip()
            text = text[:k]  # Discard '\n✿RESULT✿:'.

        return (func_name is not None), func_name, func_args, text
