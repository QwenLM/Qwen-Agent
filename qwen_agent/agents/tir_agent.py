import copy
import json
from typing import Dict, Iterator, List, Literal, Optional, Tuple, Union

import json5

from qwen_agent.agents.fncall_agent import FnCallAgent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import ASSISTANT, DEFAULT_SYSTEM_MESSAGE, Message
from qwen_agent.tools.python_executor import PythonExecutor
from qwen_agent.utils.utils import merge_generate_cfgs, print_traceback

OBS_START = '```output'
OBS_END = '\n```\n'

MAX_LLM_CALL_PER_RUN = 10


def extract_program(result: str, last_only=True):
    """
    extract the program after "```python", and before "```"
    """
    program = ''
    start = False
    for line in result.split('\n'):
        if line.startswith('```python') or line.endswith('```python'):
            if last_only:
                program = ''  # only extract the last program
            else:
                program += '\n# ========\n'
            start = True
        elif line.startswith('```'):
            start = False
        elif start:
            program += line + '\n'
    if start:
        # the code is incomplete
        program = ''
    return program


class TIRMathAgent(FnCallAgent):
    """TIR(tool-integrated reasoning) agent"""

    def __init__(self,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 **kwargs):
        super().__init__(function_list=[PythonExecutor()],
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description,
                         **kwargs)
        self.extra_generate_cfg = merge_generate_cfgs(
            base_generate_cfg=self.extra_generate_cfg,
            new_generate_cfg={'stop': [OBS_START]},
        )

    def _run(self, messages: List[Message], lang: Literal['en', 'zh'] = 'en', **kwargs) -> Iterator[List[Message]]:
        text_messages = copy.deepcopy(messages)
        num_llm_calls_available = MAX_LLM_CALL_PER_RUN
        response: str = ''
        while num_llm_calls_available > 0:
            num_llm_calls_available -= 1

            for i, msg in enumerate(text_messages):
                if isinstance(msg.content, list):
                    assert len(msg.content) == 1
                    text_messages[i].content = msg.content[0].text

            # Display the streaming response
            output = []
            for output in self._call_llm(messages=text_messages, stream=True):
                if output:
                    yield [Message(role=ASSISTANT, content=response + output[-1].content, extra=output[-1].extra)]

            # Accumulate the current response
            # The generated content before stop_word
            if not output:
                break
            response += output[-1].content

            # detect code
            has_action, action, action_input, thought = self._detect_tool(output[-1].content)
            if not has_action:
                break

            # Add the tool result
            observation = self._call_tool(action, action_input, messages=messages, **kwargs)
            try:
                observation_list = json5.loads(observation)
                if observation_list[-1] == 'Done':
                    observation = observation_list[0]
                else:
                    observation = observation_list[-1]
            except Exception:
                print_traceback()
            observation = observation.strip()
            observation = f'{OBS_START}\n{observation}{OBS_END}'

            # Accumulate the current exec result
            if not response.endswith('\n'):
                response += '\n'
            response += observation
            current_rsp = Message(role=ASSISTANT, content=response, extra=output[-1].extra)
            yield [current_rsp]

            if text_messages[-1].role == ASSISTANT:
                text_messages[-1] = current_rsp
            else:
                text_messages.append(current_rsp)

    def _detect_tool(self, text: str) -> Tuple[bool, str, str, str]:
        program = extract_program(text)
        if program:
            program = json.dumps({'code': program}, ensure_ascii=False)
        return (program != ''), PythonExecutor.name, program, text
