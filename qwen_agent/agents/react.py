from typing import Dict, Iterator, List

from qwen_agent import Agent
from qwen_agent.llm.schema import ASSISTANT, CONTENT, ROLE
from qwen_agent.utils.utils import parser_function

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


class ReAct(Agent):
    """
    Using ReAct format to call tools
    """

    def _run(self,
             messages: List[Dict],
             lang: str = 'en',
             **kwargs) -> Iterator[List[Dict]]:

        tool_descs = '\n\n'.join(
            parser_function(func.function)
            for func in self.function_map.values())
        tool_names = ','.join(tool.name for tool in self.function_map.values())

        prompt = PROMPT_REACT.format(tool_descs=tool_descs,
                                     tool_names=tool_names,
                                     query=messages[-1][CONTENT])
        messages[-1][CONTENT] = prompt

        max_turn = 5
        response = []
        while True and max_turn > 0:
            max_turn -= 1
            output_stream = self.llm.text_completion(
                messages=messages,
                stop=['Observation:', 'Observation:\n'],
            )
            output = []
            for output in output_stream:
                yield response + output
            response.extend(output)
            assert len(output) == 1 and output[-1][ROLE] == ASSISTANT
            output = output[-1][CONTENT]

            use_tool, action, action_input, output = self._detect_tool(output)
            if messages[-1][CONTENT].endswith('\nThought:'):
                if not output.startswith(' '):
                    output = ' ' + output
            else:
                if not output.startswith('\n'):
                    output = '\n' + output

            if use_tool:
                observation = self._call_tool(action, action_input)
                observation = f'\nObservation: {observation}\nThought:'
                response[-1][CONTENT] += observation
                yield response
                messages[-1][CONTENT] += output + observation
            else:
                break

    def _detect_tool_by_special_token(self, text: str):
        """
        A built-in tool call detection: After encapsulating function calls in the LLM layer, this is no longer needed

        """
        special_func_token = '\nAction:'
        special_args_token = '\nAction Input:'
        special_obs_token = '\nObservation:'
        func_name, func_args = None, None
        i = text.rfind(special_func_token)
        j = text.rfind(special_args_token)
        k = text.rfind(special_obs_token)
        if 0 <= i < j:  # If the text has `Action` and `Action input`,
            if k < j:  # but does not contain `Observation`,
                # then it is likely that `Observation` is ommited by the LLM,
                # because the output text may have discarded the stop word.
                text = text.rstrip() + special_obs_token  # Add it back.
            k = text.rfind(special_obs_token)
            func_name = text[i + len(special_func_token):j].strip()
            func_args = text[j + len(special_args_token):k].strip()
            text = text[:k]  # Discard '\nObservation:'.

        return (func_name is not None), func_name, func_args, text
