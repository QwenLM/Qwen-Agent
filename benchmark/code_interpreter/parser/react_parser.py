class ReActParser(object):

    def __init__(self):
        self.action = '\nAction:'
        self.action_input = '\nAction Input:'
        self.action_input_stop = '\nObservation:'
        self.observation = '\nObservation:'
        self.observation_stop = '\nThought:'

    def parse_latest_plugin_call(self, text):
        action = self.action
        action_input = self.action_input
        observation = self.action_input_stop
        plugin_name, plugin_args = '', ''
        i = text.rfind(action)
        j = text.rfind(action_input)
        k = text.rfind(observation)
        if 0 <= i < j:  # If the text has `Action` and `Action input`,
            if k < j:  # but does not contain `Observation`,
                # then it is likely that `Observation` is ommited by the LLM,
                # because the output text may have discarded the stop word.
                text = text.rstrip() + observation  # Add it back.
            k = text.rfind(observation)
            plugin_name = text[i + len(action):j].strip()
            plugin_args = text[j + len(action_input):k].strip()
            text = text[:k]
        return plugin_name, plugin_args, text

    def _extract_first_target(self, text, start_flag, end_flag):
        target = ''
        i = text.find(start_flag)
        if i != -1:
            j = text.find(end_flag, i)
            if j != -1:
                target = text[i + len(start_flag):j].strip()
            else:
                target = text[i + len(start_flag):].strip()
        return target

    def get_first_observation(self, text):
        return self._extract_first_target(text, self.observation, self.observation_stop)

    def get_first_action_input(self, text):
        return self._extract_first_target(text, self.action_input, self.action_input_stop)
