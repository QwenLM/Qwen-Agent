from qwen_agent.schema import RefMaterial
from qwen_agent.utils.utils import get_keyword_by_llm, get_split_word


class SimilaritySearch:

    def __init__(self):
        pass

    def run(self, line, query, max_token=4000, keyword_agent=None):
        """
        Input: one line
        Output: the relative text
        """
        content = line['raw']
        if isinstance(content, str):
            content = content.split('\n')
        if not content:
            return RefMaterial(url=line['url'], text=[]).to_dict()

        tokens = [x['token'] for x in content]
        all_tokens = sum(tokens)
        if all_tokens <= max_token:
            print('use full ref: ', all_tokens)
            return {
                'url': line['url'],
                'text': [x['page_content'] for x in content]
            }

        wordlist = get_keyword_by_llm(query, keyword_agent)
        print('wordlist: ', wordlist)
        if not wordlist:
            return RefMaterial(url=line['url'], text=[]).to_dict()

        sims = []
        for i, page in enumerate(content):
            sim = self.filter_section(page, wordlist)
            sims.append([i, sim])
        sims.sort(key=lambda item: item[1], reverse=True)
        assert len(sims) > 0

        res = []
        max_sims = sims[0][1]
        if max_sims != 0:
            manul = 2
            for i in range(min(manul, len(content))):
                res.append(content[i]['page_content'])
                max_token -= tokens[i]
            for i, x in enumerate(sims):
                if x[0] < manul:
                    continue
                page = content[x[0]]
                print('select: ', x)
                if max_token < tokens[x[0]]:
                    use_rate = (max_token / page['token']) * 0.2
                    res.append(page['page_content']
                               [:int(len(page['page_content']) * use_rate)])
                    break

                text = ''
                if isinstance(page, str):
                    text = content[x[0]]
                elif isinstance(page, dict):
                    text = page['page_content']
                res.append(text)
                max_token -= tokens[x[0]]

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
