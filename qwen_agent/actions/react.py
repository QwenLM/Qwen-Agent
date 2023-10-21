import json

from qwen_agent.actions.base import Action

from qwen_agent.tools.tools import call_plugin  # NOQA

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


class ReAct(Action):
    def __init__(self, llm=None, stream=False, list_of_plugin_info=[], prompt='default', source='dashscope'):
        super().__init__(llm=llm, stream=stream)

        self.list_of_plugin_info = list_of_plugin_info
        self.history = []
        self.prompt = prompt
        self.source = source

    def run(self, user_request, history=[], ref_doc=None, messages=None):
        prompt = self.build_input_text(user_request)
        rsp = self.run_with_tools(prompt, messages)

        return rsp

    def run_with_tools(self, prompt, messages):
        react_stop_words = ['Observation:', 'Observation:\n']

        new_messages = []
        new_messages.extend(messages)
        new_messages.append({
            'role': 'user', 'content': prompt
        })

        text = ''
        max_turn = 5
        while True and max_turn > 0:
            max_turn -= 1
            output = self.llm.chat('', messages=new_messages, stream=False, stop=react_stop_words)
            # print(new_messages)
            # print(output)
            action, action_input, output = self.parse_latest_plugin_call(output)
            if action:
                observation = call_plugin(action, action_input)
                print(observation)
                output += f'\nObservation: {observation}\nThought:'
                text += output
                new_messages[-1]['content'] += output
            else:
                text += output
                break
        return text

    def parse_latest_plugin_call(self, text):
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
            text = text[:k]
        return plugin_name, plugin_args, text

    def build_input_text(self, query):
        tool_descs = []
        tool_names = []
        for info in self.list_of_plugin_info:
            tool_descs.append(
                TOOL_DESC.format(
                    name_for_model=info['name_for_model'],
                    name_for_human=info['name_for_human'],
                    description_for_model=info['description_for_model'],
                    parameters=json.dumps(
                        info['parameters'], ensure_ascii=False),
                )
            )
            tool_names.append(info['name_for_model'])
        tool_descs = '\n\n'.join(tool_descs)
        tool_names = ','.join(tool_names)

        prompt = PROMPT_REACT.format(tool_descs=tool_descs, tool_names=tool_names, query=query)
        return prompt
