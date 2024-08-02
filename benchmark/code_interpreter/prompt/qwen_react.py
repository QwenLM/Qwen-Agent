import json
import os

from prompt.react import ReAct

QWEN_TOOLS_LIST = [
    {
        'name_for_human': '代码解释器',
        'name_for_model': 'code_interpreter',
        'description_for_model': '代码解释器，可用于执行Python代码。',
        'parameters': [{
            'name': 'code',
            'type': 'string',
            'description': '待执行的代码'
        }],
        'args_format': 'code'
    },
]

TOOL_DESC = """{name_for_model}: Call this tool to interact with the {name_for_human} API. What is the {name_for_human} API useful for? {description_for_model} Parameters: {parameters}"""


class QwenReAct(ReAct):

    def __init__(self, query, lang='en', upload_file_paths=[]):
        super().__init__(query, lang, upload_file_paths)

        self.upload_file_paths = [f'{os.path.basename(fname)}' for fname in upload_file_paths]
        self.list_of_plugin_info = QWEN_TOOLS_LIST
        self.fname_template = {
            'zh': '[上传文件{fname_str}]',
            'en': '[Upload file {fname_str}]',
            'en_multi': '[Upload file {fname_str}]'
        }

    def build_prompt(self):
        im_start = '<|im_start|>'
        im_end = '<|im_end|>'
        prompt = f'{im_start}system\nYou are a helpful assistant.{im_end}'

        query = super().build_prompt()

        query = query.lstrip('\n').rstrip()
        prompt += f'\n{im_start}user\n{query}{im_end}'
        if f'{im_start}assistant' not in query:
            prompt += f'\n{im_start}assistant\n{im_end}'
            assert prompt.endswith(f'\n{im_start}assistant\n{im_end}')

        prompt = prompt[:-len(f'{im_end}')]
        self.prompt = prompt
        return prompt

    def _build_tools_text(self):
        # tool info
        tools_text = []
        for plugin_info in self.list_of_plugin_info:
            tool = TOOL_DESC.format(
                name_for_model=plugin_info['name_for_model'],
                name_for_human=plugin_info['name_for_human'],
                description_for_model=plugin_info['description_for_model'],
                parameters=json.dumps(plugin_info['parameters'], ensure_ascii=False),
            )
            if plugin_info.get('args_format', 'json') == 'json':
                tool += ' Format the arguments as a JSON object.'
            elif plugin_info['args_format'] == 'code':
                tool += ' Enclose the code within triple backticks (`) at the beginning and end of the code.'
            else:
                raise NotImplementedError
            tools_text.append(tool)
        tools_text = '\n\n'.join(tools_text)
        return tools_text

    def _build_tools_name_text(self):
        return ', '.join([plugin_info['name_for_model'] for plugin_info in self.list_of_plugin_info])
