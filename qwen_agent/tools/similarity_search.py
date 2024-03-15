from typing import List, Union

from pydantic import BaseModel

from qwen_agent.log import logger
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.tokenization_qwen import count_tokens
from qwen_agent.utils.utils import get_split_word, parse_keyword


class RefMaterialOutput(BaseModel):
    """The knowledge data format output from the retrieval"""
    url: str
    text: list

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'text': self.text,
        }


class RefMaterialInputItem(BaseModel):
    content: str
    token: int

    def to_dict(self) -> dict:
        return {'content': self.content, 'token': self.token}


class RefMaterialInput(BaseModel):
    """The knowledge data format input to the retrieval"""
    url: str
    text: List[RefMaterialInputItem]

    def to_dict(self) -> dict:
        return {'url': self.url, 'text': [x.to_dict() for x in self.text]}


def format_input_doc(doc: List[str]) -> RefMaterialInput:
    new_doc = []
    for x in doc:
        item = RefMaterialInputItem(content=x, token=count_tokens(x))
        new_doc.append(item)
    return RefMaterialInput(url='', text=new_doc)


@register_tool('similarity_search')
class SimilaritySearch(BaseTool):
    description = '从给定文档中检索和问题相关的部分'
    parameters = [{
        'name': 'query',
        'type': 'string',
        'description': '问题，需要从文档中检索和这个问题有关的内容',
        'required': True
    }]

    def call(self,
             params: Union[str, dict],
             doc: Union[RefMaterialInput, str, List[str]] = None,
             max_token: int = 4000) -> dict:
        params = self._verify_json_format_args(params)

        query = params['query']
        if not doc:
            return {}
        if isinstance(doc, str):
            doc = [doc]
        if isinstance(doc, list):
            doc = format_input_doc(doc)

        tokens = [page.token for page in doc.text]
        all_tokens = sum(tokens)
        logger.info(f'all tokens of {doc.url}: {all_tokens}')
        if all_tokens <= max_token:
            logger.info('use full ref')
            return RefMaterialOutput(url=doc.url,
                                     text=[x.content
                                           for x in doc.text]).to_dict()

        wordlist = parse_keyword(query)
        logger.info('wordlist: ' + ','.join(wordlist))
        if not wordlist:
            return self.get_top(doc, max_token)

        sims = []
        for i, page in enumerate(doc.text):
            sim = self.filter_section(page.content, wordlist)
            sims.append([i, sim])
        sims.sort(key=lambda item: item[1], reverse=True)
        assert len(sims) > 0

        res = []
        max_sims = sims[0][1]
        if max_sims != 0:
            manul = 0
            for i in range(min(manul, len(doc.text))):
                if max_token >= tokens[
                        i] * 2:  # Ensure that the first two pages do not fill up the window
                    res.append(doc.text[i].content)
                    max_token -= tokens[i]
            for i, x in enumerate(sims):
                if x[0] < manul:
                    continue
                page = doc.text[x[0]]
                if max_token < page.token:
                    use_rate = (max_token / page.token) * 0.2
                    res.append(page.content[:int(len(page.content) *
                                                 use_rate)])
                    break

                res.append(page.content)
                max_token -= page.token

            logger.info(f'remaining slots: {max_token}')
            return RefMaterialOutput(url=doc.url, text=res).to_dict()
        else:
            return self.get_top(doc, max_token)

    def filter_section(self, text: str, wordlist: list) -> int:
        page_list = get_split_word(text)
        sim = self.jaccard_similarity(wordlist, page_list)

        return sim

    @staticmethod
    def jaccard_similarity(list1: list, list2: list) -> int:
        s1 = set(list1)
        s2 = set(list2)
        return len(s1.intersection(s2))  # avoid text length impact
        # return len(s1.intersection(s2)) / len(s1.union(s2))  # jaccard similarity

    @staticmethod
    def get_top(doc: RefMaterialInput, max_token=4000) -> dict:
        now_token = 0
        text = []
        for page in doc.text:
            if (now_token + page.token) <= max_token:
                text.append(page.content)
                now_token += page.token
            else:
                use_rate = ((max_token - now_token) / page.token) * 0.2
                text.append(page.content[:int(len(page.content) * use_rate)])
                break
        logger.info(f'remaining slots: {max_token-now_token}')
        return RefMaterialOutput(url=doc.url, text=text).to_dict()
