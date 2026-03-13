import copy
from typing import Dict, Iterator, List, Literal, Optional, Union, Tuple

from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import (
    CONTENT,
    DEFAULT_SYSTEM_MESSAGE,
    ROLE,
    USER,
    Message,
)
from qwen_agent.log import logger
from qwen_agent.tools import BaseTool
from qwen_agent.agents.assistant import Assistant
from qwen_agent.agents.react_chat import ReActChat

PLAN_PROMPT_EN = (
    "Problem: {query}"
    "Let's first understand the problem and devise a plan to solve the problem."
    " Please output the plan starting with the header '<plan>' "
    "and then followed by a tagged list of steps. "
    "Each step should start with '<step>' and end with '</step>'."
    "Please make the plan the minimum number of steps required "
    "to accurately complete the task. "
    "The final step should almost always be 'Given the above steps taken, "
    "please respond to the users original question'. "
    "At the end of your plan, output '</plan>'"
)

PLAN_PROMPT_ZH = (
    "问题：{query}"
    "先理解问题，并制定一个解决问题的计划。"
    "以'<plan>'开头，然后以列表的形式输出计划。"
    "列表中每一个步骤以<step>开头，以</step>结尾。"
    "请使计划尽可能少，以准确完成任务。"
    "最后一步应该是'根据以上步骤，请回答用户原来的问题'。"
    "在计划的末尾，输出'</plan>'"
)

EXECUTE_PROMPT_EN = """Previous steps:
{previous_steps}
Current objective:
{current_step}
Complete the current objective.
"""

EXECUTE_PROMPT_ZH = """前置步骤：
{previous_steps}
当前目标：
{current_step}
完成当前目标。
"""


class PlanAndExecuteAgent(Assistant):
    """Plan and Execute Agent."""

    def __init__(
        self,
        function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
        llm_planner: Optional[Union[Dict, BaseChatModel]] = None,
        llm_executor: Optional[Union[Dict, BaseChatModel]] = None,
        system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
        name: Optional[str] = None,
        description: Optional[str] = None,
        files: Optional[List[str]] = None,
        rag_cfg: Optional[Dict] = None,
    ):
        super().__init__(
            function_list=function_list,
            llm=llm_planner,
            system_message=system_message,
            name=name,
            description=description,
            files=files,
            rag_cfg=rag_cfg,
        )
        self.executor = ReActChat(
            llm=llm_executor, function_list=function_list, files=files
        )

    def _parse_steps(self, message: Message) -> List[Message]:
        import re

        pattern = re.compile(
            r"<step\b[^>]*>(.*?)</step\b[^>]*>", re.DOTALL | re.IGNORECASE
        )
        return [
            match.group(1).strip()
            for match in pattern.finditer(message[CONTENT])
            if match.group(1).strip()
        ]

    def _prepare_step_prompt(
        self,
        previous_steps: List[Tuple[str, str]],
        current_step: str,
        lang: Literal["en", "zh"] = "en",
    ) -> str:
        prompt = EXECUTE_PROMPT_EN if lang == "en" else EXECUTE_PROMPT_ZH
        previous_steps_text = ""
        for i, (objective, result) in enumerate(previous_steps):
            if lang == "zh":
                previous_steps_text += (
                    f"步骤 {i+1}:\n- 目标: {objective}\n- 结果: {result}\n"
                )
            else:
                previous_steps_text += (
                    f"Step {i+1}:\n- Objective: {objective}\n- Result: {result}\n"
                )
        return [
            Message(
                role=USER,
                content=prompt.format(
                    previous_steps=previous_steps_text, current_step=current_step
                ),
            )
        ]

    def _run(
        self,
        messages: List[Message],
        lang: Literal["en", "zh"] = "en",
        knowledge: str = "",
        **kwargs,
    ) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)

        # Plan
        plan_prompt = PLAN_PROMPT_EN if lang == "en" else PLAN_PROMPT_ZH
        if messages and messages[-1][ROLE] == USER:
            query = messages[-1][CONTENT]
            messages[-1][CONTENT] = plan_prompt.format(query=query)
        response = []
        for rsp in super()._run(
            messages=messages, lang=lang, knowledge=knowledge, **kwargs
        ):
            yield response + rsp
        response += rsp

        # Execute
        steps = self._parse_steps(response[-1])
        step_container = []
        for step in steps:
            new_message = self._prepare_step_prompt(step_container, step)
            logger.debug(f'Step {len(step_container)+1}: {step}')
            for rsp in self.executor.run(messages=new_message, lang=lang, **kwargs):
                yield response + rsp
            step_container.append((step, rsp[-1][CONTENT]))
            response += rsp
        yield response
