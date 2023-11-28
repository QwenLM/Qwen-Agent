import copy
from typing import Dict, List

from qwen_agent.actions import GenKeyword
from qwen_agent.memory.similarity_search import SimilaritySearch
from qwen_agent.utils.tokenization_qwen import count_tokens


# TODO: Design the interface.
class Memory:

    def __init__(self, llm=None, stream=False):
        self.search_agent = SimilaritySearch()
        self.keyword_agent = GenKeyword(llm=llm, stream=stream)

    def get(self, query: str, records: list, max_token=4000) -> List[Dict]:
        # token counter backup
        new_records = []
        for record in records:
            if not record['raw']:
                continue
            if 'token' not in record['raw'][0]['page_content']:
                tmp = []
                for page in record['raw']:
                    new_page = copy.deepcopy(page)
                    new_page['token'] = count_tokens(page['page_content'])
                    tmp.append(new_page)
                record['raw'] = tmp
            new_records.append(record)
        records = new_records

        single_max_token = int(max_token / len(records))
        _ref_list = []
        for record in records:
            now_ref_list = self.search_agent.run(record, query,
                                                 single_max_token,
                                                 self.keyword_agent)
            if now_ref_list['text']:
                _ref_list.append(now_ref_list)

        if not _ref_list:
            _ref_list = self.get_top(records,
                                     single_max_token=single_max_token)

        return _ref_list

    def get_top(self, records: list, single_max_token=4000):
        _ref_list = []
        for record in records:
            now_token = 0
            raw = record['raw']
            tmp = {'url': record['url'], 'text': []}
            for page in raw:
                if (now_token + page['token']) <= single_max_token:
                    tmp['text'].append(page['page_content'])
                    now_token += page['token']
                else:
                    use_rate = (
                        (single_max_token - now_token) / page['token']) * 0.2
                    tmp['text'].append(
                        page['page_content']
                        [:int(len(page['page_content']) * use_rate)])
                    break

            _ref_list.append(tmp)
        return _ref_list
