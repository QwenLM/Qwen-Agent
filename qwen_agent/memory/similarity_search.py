from qwen_agent.schema import RefMaterial
from qwen_agent.utils.util import get_split_word


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

        content = line['raw']
        if isinstance(content, str):
            content = content.split('\n')

        res = []
        sims = []
        for i, page in enumerate(content):
            sim = self.filter_section(page, wordlist)
            sims.append([i, sim])
        sims.sort(key=lambda x: x[1], reverse=True)
        # print('sims: ', sims)
        max_sims = sims[0][1]
        if max_sims != 0:
            for i, x in enumerate(sims):
                if x[1] < max_sims and i > 3:
                    break
                page = content[x[0]]
                text = ''
                if isinstance(page, str):
                    text = content[x[0]]
                elif isinstance(page, dict):
                    text = page['page_content']
                res.append(text)
            # for x in res:
            #     print("=========")
            #     print(x)
        return RefMaterial(url=line['url'], text=res).to_dict()

    def filter_section(self, page, wordlist):
        if isinstance(page, str):
            text = page
        elif isinstance(page, dict):
            text = page['page_content']
        else:
            print(type(page))
            raise TypeError

        pagelist = get_split_word(text)
        sim = self.jaccard_similarity(wordlist, pagelist)

        return sim

    def jaccard_similarity(self, list1, list2):
        s1 = set(list1)
        s2 = set(list2)
        return len(s1.intersection(s2))  # avoid text length impact
        # return len(s1.intersection(s2)) / len(s1.union(s2))  # jaccard similarity
