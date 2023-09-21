from prompt.react import ReAct


class LlamaReAct(ReAct):
    def __init__(self, query, lang='en', upload_file_paths=[]):
        super().__init__(query, lang, upload_file_paths)

    def build_prompt(self):
        planning_prompt = super().build_prompt()
        planning_prompt = '[INST] ' + planning_prompt + ' [/INST]'
        return planning_prompt

    def postprocess_prompt(self):
        if '<|im_end|>' in self.query:
            self.prompt = self.prompt.replace('<|im_end|>\n<|im_start|>assistant', ' [/INST] ')
            assert self.prompt.endswith(' [/INST]')
            self.prompt = self.prompt[: -len(' [/INST]')]
        return self.prompt
