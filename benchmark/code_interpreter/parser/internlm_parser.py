from parser.react_parser import ReActParser


class InternLMReActParser(ReActParser):

    def __init__(self):
        self.action = '\nAction:'
        self.action_input = '\nActionInput:'
        self.action_input_stop = '<eoa>'
        self.observation = '<|System|>:Response:'
        self.observation_stop = '<TOKENS_UNUSED_2>\n<|Bot|>:'
