from abc import abstractmethod


class LLMBase:
    def __init__(self, model='qwen', api_key='',):

        self.model = model
        self.memory = None
        self.api_key = api_key.strip()

    def chat(self, query, stream=False, messages=None):
        if stream:
            return self.chat_stream(query, messages)
        else:
            return self.chat_no_stream(query, messages)

    @abstractmethod
    def chat_stream(self, query, messages=None):
        """
        :param query: str
        :param messages: List[dict]
        :return: str
        """
        raise NotImplementedError

    @abstractmethod
    def chat_no_stream(self, query, messages=None):
        """
        :param query: str
        :param messages: List[dict]
        :return: Iterator[str]
        """
        raise NotImplementedError
