import os

tools_text = """code_interpreter: Call this tool to interact with the Code Interpreter API.
What is the Code Interpreter API useful for?
Code Interpreter is used to execute Python code to deal with the following tasks:
1. Solving mathematical problems, both quantitative and qualitative
2. Doing data analysis and visualization
3. Converting files between formats
Parameters:
```py
code
```
Enclose the code within triple backticks (```) at the beginning and end of the code.
"""

REACT_PROMPT = """Answer the following questions as best you can. You have access to the following tools:

{tools_text}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tools_name_text}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {query}"""

fname_template = {
    'zh': '文件{fname_str}，',
    'en_multi': 'Files {fname_str}. ',
    'en': 'File {fname_str}. ',
}


class ReAct(object):

    def __init__(self, query, lang='en', upload_file_paths=[]):
        self.query = query
        self.lang = lang
        self.upload_file_paths = [f'`{os.path.basename(fname)}`' for fname in upload_file_paths]

        self.fname_template = fname_template
        self.react_template = REACT_PROMPT
        self.prompt = ''

    def build_prompt(self):
        query = self._format_upload_fname() + self.query
        tools_text = self._build_tools_text()
        tools_name_text = self._build_tools_name_text()
        planning_prompt = self.react_template.format(query=query,
                                                     tools_text=tools_text,
                                                     tools_name_text=tools_name_text)

        self.prompt = planning_prompt
        return planning_prompt

    def _format_upload_fname(self):
        prefix = ''
        if self.upload_file_paths:
            fname_str = ', '.join(self.upload_file_paths)
            lang_key = 'en_multi' if self.lang == 'en' and len(self.upload_file_paths) > 1 else self.lang
            fname_template = self.fname_template[lang_key]
            prefix = fname_template.format(fname_str=fname_str)
        return prefix

    def _build_tools_text(self):
        return tools_text

    def _build_tools_name_text(self):
        return 'code_interpreter'

    def build_observation(self, observation):
        return f'\nObservation: {observation}\nThought:'

    def get_stop_words_list(self):
        return ['Observation:', 'Observation:\n']
