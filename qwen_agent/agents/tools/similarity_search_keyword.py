from qwen_agent.agents.schema import RefMaterial
from qwen_agent.utils.util import get_key_word


class SSKeyWord:
    def __init__(self, llm=None, stream=False):
        self.llm = llm
        self.stream = stream

    def run(self, line, query):
        """
        Input: one line
        Output: the relative text
        """
        wordlist = get_key_word(query)

        content = line['raw']
        if isinstance(content, str):
            content = content.split('\n')

        res = []
        for page in content:
            rel_text = self.filter_section(page, wordlist)
            if rel_text:
                res.append(rel_text)
        return RefMaterial(url=line['url'], text=res).to_dict()

    def filter_section(self, page, wordlist):
        if isinstance(page, str):
            text = page
        elif isinstance(page, dict):
            text = page['page_content']
        else:
            print(type(page))
            raise TypeError

        for x in wordlist:
            if x in text:
                return text
        return ''
