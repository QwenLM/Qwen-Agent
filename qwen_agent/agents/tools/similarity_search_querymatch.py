from qwen_agent.agents.schema import RefMaterial
from qwen_agent.utils.util import get_key_word


class SSQueryMatch:
    def __init__(self, llm=None, stream=False):
        self.llm = llm
        self.stream = stream

    def run(self, doc, query):
        """
        Input: lines
        Output: the relative text
        """
        wordlist = get_key_word(query)

        res = []
        for page in doc['raw']:
            # print(page)
            rel_text = self.filter_section(page, wordlist)
            if rel_text:
                res.append(rel_text)
        return RefMaterial(url=doc['url'], text=res).to_dict()

    def filter_section(self, page, wordlist):
        # 按照段落匹配关键词，只要存在重复词，则加入候选集
        text = page['related_questions']
        res = ''
        for x in wordlist:
            if x in text:
                res = page['page_content']
                break
        return res
