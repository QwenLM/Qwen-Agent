from prompt.react import ReAct

INTERNLM_TOOL_DESCRIPTION = """用来执行Python代码。代码必须是一个函数，
函数名必须得是 'solution'，代码对应你的思考过程。代码实例格式如下：
```python
# import 依赖包
import xxx
def solution():
    # 初始化一些变量
    variable_names_with_real_meaning = xxx
    # 步骤一
    mid_variable = func(variable_names_with_real_meaning)
    # 步骤 x
    mid_variable = func(mid_variable)
    # 最后结果
    final_answer =  func(mid_variable)
    return final_answer
```"""

INTERNLM_TOOL = {'PythonInterpreter': INTERNLM_TOOL_DESCRIPTION}

INTERNLM_REACT_PROMPT_ZH = """<|System|>:你是一个可以调用外部工具的助手，可以使用的工具包括：
{tools_text}
如果使用工具请遵循以下格式回复：
```
Thought:思考你当前步骤需要解决什么问题，是否需要使用工具
Action:工具名称，你的工具必须从 [{tools_name_text}] 选择
ActionInput:工具输入参数
```
工具返回按照以下格式回复：
```
Response:调用工具后的结果
```
如果你已经知道了答案，或者你不需要工具，请遵循以下格式回复
```
Thought:给出最终答案的思考过程
FinalAnswer:最终答案
```
开始!<TOKENS_UNUSED_2>
<|User|>:{query}<eoh>
<|Bot|>:"""

INTERNLM_REACT_PROMPT_EN = """<|System|>:You are a assistant who can utilize external tools.
{tools_text}
To use a tool, please use the following format:
```
Thought: Think what you need to solve, do you need to use tools?
Action: the tool name, should be one of [{tools_name_text}]
ActionInput: the input to the action
```
The response after utilizing tools should using the following format:
```
Response: the results after call the tool.
``
If you already know the answer, or you do not need to use tools,
please using the following format to reply:
```
Thought: the thought process to get the final answer
FinalAnswer: final answer
```
Begin!<TOKENS_UNUSED_2>
<|User|>:{query}<eoh>
<|Bot|>:"""


class InternLMReAct(ReAct):

    def __init__(self, query, lang='en', upload_file_paths=[]):
        super().__init__(query, lang, upload_file_paths)
        self.react_template = INTERNLM_REACT_PROMPT_ZH if self.lang == 'zh' else INTERNLM_REACT_PROMPT_EN

    def build_prompt(self):
        planning_prompt = super().build_prompt()
        if '<|im_end|>' in self.query and planning_prompt.endswith('<eoh>\n<|Bot|>:'):
            planning_prompt = planning_prompt[:-len('<eoh>\n<|Bot|>:')]

        if '<|im_end|>' in self.query:
            planning_prompt = planning_prompt.replace('<|im_end|>\n<|im_start|>assistant\n', '<eoh>\n<|Bot|>:').replace(
                'Observation:',
                '<eoa>\n<|System|>:Response:').replace('\nAction Input',
                                                       '\nActionInput').replace('code_interpreter', 'PythonInterpreter')
            assert planning_prompt.endswith('Thought:')
            planning_prompt = planning_prompt[:-len('Thought:')] + '<TOKENS_UNUSED_2>\n<|Bot|>:'

        self.prompt = planning_prompt
        return planning_prompt

    def _build_tools_text(self):
        return INTERNLM_TOOL

    def _build_tools_name_text(self):
        return list(INTERNLM_TOOL.keys())

    def build_observation(self, observation):
        return f'<eoa>\n<|System|>:Response:{observation}\n<TOKENS_UNUSED_2>\n<|Bot|>:'

    def get_stop_words_list(self):
        return ['<eoa>']
