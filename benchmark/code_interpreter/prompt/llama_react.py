from prompt.react import ReAct


class LlamaReAct(ReAct):

    def __init__(self, query, lang='en', upload_file_paths=[]):
        super().__init__(query, lang, upload_file_paths)

    def build_prompt(self):
        planning_prompt = super().build_prompt()
        planning_prompt = '[INST] ' + planning_prompt + ' [/INST]'

        if '<|im_end|>' in self.query:
            planning_prompt = planning_prompt.replace('<|im_end|>\n<|im_start|>assistant', ' [/INST] ')
            assert planning_prompt.endswith(' [/INST]')
            planning_prompt = planning_prompt[:-len(' [/INST]')]

        self.prompt = planning_prompt
        return planning_prompt
