import importlib

from qwen_agent.tools import SimilaritySearchType


class SimilaritySearch:
    def __init__(self, type='keyword', llm=None, stream=False):
        self.type = type
        if type == SimilaritySearchType.KeyWord.value:
            module = 'qwen_agent.tools.similarity_search_keyword'
            run_func = importlib.import_module(module).SSKeyWord(llm, stream).run
        elif type == SimilaritySearchType.QueryMatch.value:
            module = 'qwen_agent.tools.similarity_search_querymatch'
            run_func = importlib.import_module(module).SSQueryMatch(llm, stream).run
        elif type == SimilaritySearchType.LLM.value:
            module = 'qwen_agent.tools.similarity_search_llm'
            run_func = importlib.import_module(module).SSLLM(llm).run
        else:
            raise NotImplementedError
        self.run_func = run_func

    def run(self, path, query):
        return self.run_func(path, query)
