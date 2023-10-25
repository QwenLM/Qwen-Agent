from typing import Dict, List

from qwen_agent.memory.similarity_search import SimilaritySearch
from qwen_agent.schema import RefMaterial
from qwen_agent.utils.utils import count_tokens


# TODO: Design the interface.
class Memory:

    def __init__(self):
        pass

    def get(self,
            query: str,
            records: list,
            llm=None,
            stream=False,
            max_token=4000) -> List[Dict]:

        search_agent = SimilaritySearch(llm=llm, stream=stream)
        _ref_list = []
        for record in records:
            now_ref_list = search_agent.run(record, query)
            if now_ref_list['text']:
                _ref_list.append(now_ref_list)

        if not _ref_list:
            _ref_list = self.get_top(records)
        # token number
        new_ref_list = []
        single_max_token = int(max_token / len(_ref_list))
        for _ref in _ref_list:
            tmp = {'url': _ref['url'], 'text': []}
            now_token = 0
            print(len(_ref['text']))
            for x in _ref['text']:
                # lenx = len(x)
                lenx = count_tokens(x)
                if (now_token + lenx) <= single_max_token:
                    tmp['text'].append(x)
                    now_token += lenx
                else:
                    use_rate = (single_max_token - now_token) / lenx
                    tmp['text'].append(x[:int(len(x) * use_rate)])
                    break
            new_ref_list.append(tmp)

        return new_ref_list

    def get_top(self, records: list, k=6):
        _ref_list = []
        for record in records:
            raw = record['raw']
            k = min(len(raw), k)
            _ref_list.append(
                RefMaterial(url=record['url'],
                            text=[x['page_content']
                                  for x in raw[:k]]).to_dict())
        return _ref_list
