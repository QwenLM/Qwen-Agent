from qwen_agent.schema import RefMaterial
from qwen_agent.utils.utils import get_split_word


class SimilaritySearch:

    def __init__(self, llm=None, stream=False):
        self.llm = llm
        self.stream = stream

    def run(self, line, query):
        """
        Input: one line
        Output: the relative text
        """
        wordlist = get_split_word(query)
        if not wordlist:
            return RefMaterial(url=line['url'], text=[]).to_dict()

        content = line['raw']

        res = []
        sims = []
        for i, page in enumerate(content):
            sim = self.filter_section(page, wordlist)
            sims.append([i, sim])
        sims.sort(key=lambda item: item[1], reverse=True)

        assert len(sims) > 0
        found_page_first = {0: False, 1: False}

        max_sims = sims[0][1]
        if max_sims != 0:
            for i, x in enumerate(sims):
                if i > 3:
                    break
                page = content[x[0]]
                text = page['page_content']
                res.append(text)
                if x[0] in found_page_first.keys():
                    found_page_first[x[0]] = True

            # manually add pages
            for k in found_page_first.keys():
                if k >= len(content):
                    break
                if not found_page_first[k]:
                    page = content[k]
                    text = page['page_content']
                    res.append(text)

        return RefMaterial(url=line['url'], text=res).to_dict()

    def filter_section(self, page, wordlist):
        text = page['page_content']

        page_list = get_split_word(text)
        sim = self.jaccard_similarity(wordlist, page_list)

        return sim

    def jaccard_similarity(self, list1, list2):
        s1 = set(list1)
        s2 = set(list2)
        return len(s1.intersection(s2))  # avoid text length impact
        # return len(s1.intersection(s2)) / len(s1.union(s2))  # jaccard similarity
