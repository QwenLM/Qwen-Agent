from qwen_agent.tools import SimilaritySearchType


class SimilaritySearch:
    def __init__(self, type='keyword', llm=None, stream=False):
        self.type = type
        if type == SimilaritySearchType.KeyWord.value:
            from qwen_agent.tools.similarity_search_keyword import SSKeyWord
            run_func = SSKeyWord(llm, stream).run
        elif type == SimilaritySearchType.QueryMatch.value:
            from qwen_agent.tools.similarity_search_querymatch import SSQueryMatch
            run_func = SSQueryMatch(llm, stream).run
        elif type == SimilaritySearchType.LLM.value:
            from qwen_agent.tools.similarity_search_llm import SSLLM
            run_func = SSLLM(llm).run
        elif type == SimilaritySearchType.Jaccard.value:
            from qwen_agent.tools.similarity_search_jaccard import SSJaccard
            run_func = SSJaccard(llm, stream).run
        else:
            raise NotImplementedError
        self.run_func = run_func

    def run(self, path, query):
        return self.run_func(path, query)
