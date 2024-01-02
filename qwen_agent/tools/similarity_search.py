import json
from typing import List

from pydantic import BaseModel

from qwen_agent.log import logger
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import get_keyword_by_llm, get_split_word


class RefMaterialOutput(BaseModel):
    """
    The knowledge data format output from the retrieval
    """
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
    """
    The knowledge data format input to the retrieval
    """
    url: str
    text: List[RefMaterialInputItem]

    def to_dict(self) -> dict:
        return {'url': self.url, 'text': [x.to_dict() for x in self.text]}


@register_tool('retrieval')
class SimilaritySearch(BaseTool):
    name = 'retrieval'
    description = '从文档中检索和问题相关的部分，从而辅助回答问题'
    parameters = [{
        'name': 'query',
        'type': 'string',
        'description': '待回答的问题',
        'required': True
    }]

    def call(self,
             params: str,
             doc: RefMaterialInput = None,
             max_token: int = 4000,
             **kwargs) -> str:
        """
        This tool is usually used by doc_parser tool

        :param doc: Knowledge base to be queried
        :param query: the query to retrieve
        :param max_token: the max token number
        :return: RefMaterialOutput
        """
        params = self._verify_args(params)
        if isinstance(params, str):
            return 'Parameter Error'
        query = params['query']
        assert doc is not None, 'must provide doc object'

        tokens = [page.token for page in doc.text]
        all_tokens = sum(tokens)
        logger.info(f'all tokens of {doc.url}: {all_tokens}')
        if all_tokens <= max_token:
            logger.info('use full ref')
            return json.dumps(RefMaterialOutput(
                url=doc.url, text=[x.content for x in doc.text]).to_dict(),
                              ensure_ascii=False)

        wordlist = get_keyword_by_llm(query)
        logger.info('wordlist: ' + ','.join(wordlist))
        if not wordlist:
            return json.dumps(self.get_top(doc, max_token).to_dict(),
                              ensure_ascii=False)

        sims = []
        for i, page in enumerate(doc.text):
            sim = self.filter_section(page.content, wordlist)
            sims.append([i, sim])
        sims.sort(key=lambda item: item[1], reverse=True)
        assert len(sims) > 0

        res = []
        max_sims = sims[0][1]
        if max_sims != 0:
            manul = 2
            for i in range(min(manul, len(doc.text))):
                res.append(doc.text[i].content)
                max_token -= tokens[i]
            for i, x in enumerate(sims):
                if x[0] < manul:
                    continue
                page = doc.text[x[0]]
                print('select: ', x)
                if max_token < page.token:
                    use_rate = (max_token / page.token) * 0.2
                    res.append(page.content[:int(len(page.content) *
                                                 use_rate)])
                    break

                res.append(page.content)
                max_token -= page.token

            logger.info(f'remaining slots: {max_token}')
            return json.dumps(RefMaterialOutput(url=doc.url,
                                                text=res).to_dict(),
                              ensure_ascii=False)
        else:
            return json.dumps(self.get_top(doc, max_token).to_dict(),
                              ensure_ascii=False)

    def filter_section(self, text: str, wordlist: list) -> int:
        page_list = get_split_word(text)
        sim = self.jaccard_similarity(wordlist, page_list)

        return sim

    def jaccard_similarity(self, list1: list, list2: list) -> int:
        s1 = set(list1)
        s2 = set(list2)
        return len(s1.intersection(s2))  # avoid text length impact
        # return len(s1.intersection(s2)) / len(s1.union(s2))  # jaccard similarity

    def get_top(self,
                doc: RefMaterialInput,
                max_token=4000,
                **kwargs) -> RefMaterialOutput:
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
        return RefMaterialOutput(url=doc.url, text=text)
