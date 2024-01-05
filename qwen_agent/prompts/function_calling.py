from typing import Dict, Iterator, List, Optional

from qwen_agent import Agent
from qwen_agent.log import logger
from qwen_agent.prompts.react import ReAct
from qwen_agent.prompts.react_chat import ReActChat


class FunctionCalling(Agent):

    def _run(self,
             user_request,
             history: Optional[List[Dict]] = None,
             lang: str = 'en') -> Iterator[str]:

        if not self.llm.support_function_calling():
            if self.llm.support_raw_prompt():
                logger.info(
                    'this model does not support function calling, using ReAct'
                )
                react = ReAct(function_list=self.function_list, llm=self.llm)
                return react.run(user_request, history=history, lang=lang)
            else:
                logger.info(
                    'this model does not support function calling and ReAct-continue, using ReAct-Chat'
                )
                react_chat = ReActChat(function_list=self.function_list,
                                       llm=self.llm)
                return react_chat.run(user_request, history=history, lang=lang)
        else:
            logger.info('beging function calling... ')
            return self._run_with_func_call(user_request,
                                            history=history,
                                            lang=lang)

    def _run_with_func_call(self,
                            user_request,
                            history: Optional[List[Dict]] = None,
                            lang: str = 'en') -> Iterator[str]:
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
