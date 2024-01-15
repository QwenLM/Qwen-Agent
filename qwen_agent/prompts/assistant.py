from typing import Dict, Iterator, List

from qwen_agent import Agent
from qwen_agent.llm.schema import CONTENT, ROLE, SYSTEM

KNOWLEDGE_TEMPLATE_ZH = """

# 知识库

{knowledge}

"""

KNOWLEDGE_TEMPLATE_EN = """

# Knowledge Base

{knowledge}

"""

KNOWLEDGE_TEMPLATE = {'zh': KNOWLEDGE_TEMPLATE_ZH, 'en': KNOWLEDGE_TEMPLATE_EN}

SPECIAL_PREFIX_TEMPLATE = {
    'zh': '(你可以使用工具：[{tool_names}])',
    'en': '(You have access to tools: [{tool_names}])',
}


class Assistant(Agent):

    def _run(self,
             messages: List[Dict],
             knowledge: str = '',
             lang: str = 'zh') -> Iterator[List[Dict]]:

        system_prompt = ''
        if knowledge:
            system_prompt += KNOWLEDGE_TEMPLATE[lang].format(
                knowledge=knowledge)

        query_prefix = ''
        if self.function_map:
            # This query_prefix may discard
            tool_names = ','.join(tool.name
                                  for tool in self.function_map.values())
            query_prefix = SPECIAL_PREFIX_TEMPLATE[lang].format(
                tool_names=tool_names)

        if messages[0][ROLE] == SYSTEM:
            messages[0][CONTENT] += system_prompt
        else:
            messages.insert(0, {ROLE: SYSTEM, CONTENT: system_prompt})

        # concat the new messages
        messages[-1][CONTENT] = query_prefix + messages[-1][CONTENT]

        max_turn = 5
        response = []
        while True and max_turn > 0:
            max_turn -= 1
            output_stream = self._call_llm(
                messages=messages,
                functions=[
                    func.function for func in self.function_map.values()
                ])
            output = []
            for output in output_stream:
                yield response + output
            response.extend(output)
            messages.extend(output)
            # logger.info(json.dumps(response, ensure_ascii=False))

            use_tool, action, action_input, _ = self._detect_tool(response[-1])
            if use_tool:
                observation = self._call_tool(action, action_input)
                fn_msg = {
                    'role': 'function',
                    'name': action,
                    'content': observation,
                }
                messages.append(fn_msg)
                response.append(fn_msg)
                yield response
            else:
                break
