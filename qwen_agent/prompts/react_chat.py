from typing import Dict, Iterator, List, Optional

from qwen_agent import Agent

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


class ReActChat(Agent):

    def _run(self,
             user_request,
             history: Optional[List[Dict]] = None,
             lang: str = 'en') -> Iterator[str]:

        self.tool_descs = '\n\n'.join(tool.function_plain_text
                                      for tool in self.function_map.values())
        self.tool_names = ','.join(tool.name
                                   for tool in self.function_map.values())

        messages = []
        if history:
            assert history[-1][
                'role'] != 'user', 'The history should not include the latest user query.'
            messages.extend(history)

        prompt = PROMPT_REACT.format(tool_descs=self.tool_descs,
                                     tool_names=self.tool_names,
                                     query=user_request)
        messages.append({'role': 'user', 'content': prompt})

        max_turn = 5
        while True and max_turn > 0:
            max_turn -= 1
            output = self.llm.chat(
                messages=messages,
                stream=False,
                stop=['Observation:', 'Observation:\n'],
            )
            use_tool, action, action_input, output = self._detect_tool(output)
            if messages[-1]['content'].endswith('\nThought:'):
                if not output.startswith(' '):
                    output = ' ' + output
            else:
                if not output.startswith('\n'):
                    output = '\n' + output
            yield output
            if use_tool:
                observation = self._call_tool(action, action_input)
                observation = f'\nObservation: {observation}\nThought:'
                yield observation
                messages[-1]['content'] += output + observation
            else:
                break
