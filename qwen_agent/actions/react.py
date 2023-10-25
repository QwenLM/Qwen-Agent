import json
from typing import Dict, Iterator, List, Optional

from qwen_agent.actions.base import Action
from qwen_agent.tools import call_plugin

TOOL_DESC = """{name_for_model}: Call this tool to interact with the {name_for_human} API. What is the {name_for_human} API useful for? {description_for_model} Parameters: {parameters}"""

PROMPT_REACT = """Answer the following questions as best you can. You have access to the following tools:

{tool_descs}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {query}"""


def _build_react_instruction(query: str, functions: List[Dict]):
    tool_descs = []
    tool_names = []
    for info in functions:
        tool_descs.append(
            TOOL_DESC.format(
                name_for_model=info['name_for_model'],
                name_for_human=info['name_for_human'],
                description_for_model=info['description_for_model'],
                parameters=json.dumps(info['parameters'], ensure_ascii=False),
            ))
        tool_names.append(info['name_for_model'])
    tool_descs = '\n\n'.join(tool_descs)
    tool_names = ','.join(tool_names)

    prompt = PROMPT_REACT.format(tool_descs=tool_descs,
                                 tool_names=tool_names,
                                 query=query)
    return prompt


def _parse_last_action(text):
    plugin_name, plugin_args = '', ''
    i = text.rfind('\nAction:')
    j = text.rfind('\nAction Input:')
    k = text.rfind('\nObservation:')
    if 0 <= i < j:  # If the text has `Action` and `Action input`,
        if k < j:  # but does not contain `Observation`,
            # then it is likely that `Observation` is ommited by the LLM,
            # because the output text may have discarded the stop word.
            text = text.rstrip() + '\nObservation:'  # Add it back.
        k = text.rfind('\nObservation:')
        plugin_name = text[i + len('\nAction:'):j].strip()
        plugin_args = text[j + len('\nAction Input:'):k].strip()
        text = text[:k]  # Discard '\nObservation:'.
    return plugin_name, plugin_args, text


# TODO: When to put an parameter (such as history) in __init__()? When to put it in run()?
class ReAct(Action):

    def _run(self,
             user_request,
             functions: List[Dict] = None,
             history: Optional[List[Dict]] = None,
             lang: str = 'en') -> Iterator[str]:
        functions = functions or []
        prompt = _build_react_instruction(user_request, functions)

        messages = []
        if history:
            assert history[-1][
                'role'] != 'user', 'The history should not include the latest user query.'
            messages.extend(history)
        messages.append({'role': 'user', 'content': prompt})

        max_turn = 5
        while True and max_turn > 0:
            max_turn -= 1
            output = self.llm.chat(
                messages=messages,
                stream=False,  # TODO:
                stop=['Observation:', 'Observation:\n'],
            )
            action, action_input, output = _parse_last_action(output)
            if messages[-1]['content'].endswith('\nThought:'):
                if not output.startswith(' '):
                    output = ' ' + output
            else:
                if not output.startswith('\n'):
                    output = '\n' + output
            yield output
            if action:
                observation = call_plugin(action, action_input)
                observation = f'\nObservation: {observation}\nThought:'
                yield observation
                messages[-1]['content'] += output + observation
            else:
                break
