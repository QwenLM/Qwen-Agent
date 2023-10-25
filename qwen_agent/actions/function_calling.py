from typing import Dict, Iterator, List

from qwen_agent.actions.base import Action
from qwen_agent.actions.react import ReAct
from qwen_agent.tools import call_plugin


class FunctionCalling(Action):

    def run(self, user_request, functions: List[Dict] = None) -> Iterator[str]:
        functions = functions or []

        if not self.llm.support_function_calling():
            return ReAct(llm=self.llm,
                         stream=self.stream).run(user_request,
                                                 functions=functions)

        messages = [{'role': 'user', 'content': user_request}]
        is_first_yield = True
        while True:
            rsp = self.llm.chat_with_functions(
                messages=messages,
                functions=functions,
            )
            if is_first_yield:
                is_first_yield = False
            else:
                yield '\n'
            if rsp.get('function_call', None):
                yield rsp['content']
                yield '\nAction: ' + rsp['function_call']['name']
                yield '\nAction Input:\n'
                yield rsp['function_call']['arguments']

                bot_msg = {
                    'role': 'assistant',
                    'content': rsp['content'],
                    'function_call': {
                        'name': rsp['function_call']['name'],
                        'arguments': rsp['function_call']['arguments'],
                    },
                }
                messages.append(bot_msg)

                obs = call_plugin(rsp['function_call']['name'],
                                  rsp['function_call']['arguments'])
                yield '\nObservation: ' + obs + '\n'

                fn_msg = {
                    'role': 'function',
                    'name': rsp['function_call']['name'],
                    'content': obs,
                }
                messages.append(fn_msg)
            else:
                yield 'Thought: I now know the final answer.'
                yield '\nFinal Answer: ' + rsp['content']
                bot_msg = {
                    'role': 'assistant',
                    'content': rsp['content'],
                }
                messages.append(bot_msg)
                break
