from typing import Dict, Iterator, List, Optional

from qwen_agent import Agent
from qwen_agent.lite_agents.react import ReAct


class FunctionCalling(Agent):

    def _run(self,
             user_request,
             history: Optional[List[Dict]] = None,
             lang: str = 'en') -> Iterator[str]:

        if not self.llm.support_function_calling():
            react = ReAct(function_list=self.function_list, llm=self.llm)
            return react.run(user_request, history=history, lang=lang)
        messages = []
        if history:
            assert history[-1][
                'role'] != 'user', 'The history should not include the latest user query.'
            messages.extend(history)

        messages = [{'role': 'user', 'content': user_request}]
        is_first_yield = True
        while True:
            rsp = self.llm.chat_with_functions(
                messages=messages,
                functions=[
                    func.function for func in self.function_map.values()
                ],
            )
            if is_first_yield:
                is_first_yield = False
            else:
                yield '\n'
            use_tool, action, action_input, output = self._detect_tool(rsp)
            if use_tool:
                yield output
                yield '\nAction: ' + action
                yield '\nAction Input:\n'
                yield action_input

                bot_msg = {
                    'role': 'assistant',
                    'content': output,
                    'function_call': {
                        'name': action,
                        'arguments': action_input,
                    },
                }
                messages.append(bot_msg)

                obs = self._call_tool(action, action_input)
                yield '\nObservation: ' + obs + '\n'

                fn_msg = {
                    'role': 'function',
                    'name': action,
                    'content': obs,
                }
                messages.append(fn_msg)
            else:
                yield 'Thought: I now know the final answer.'
                yield '\nFinal Answer: ' + output
                bot_msg = {
                    'role': 'assistant',
                    'content': output,
                }
                messages.append(bot_msg)
                break
