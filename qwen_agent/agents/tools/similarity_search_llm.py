import json

from qwen_agent.agents.schema import RefMaterial
from qwen_agent.llm.qwen import qwen_chat_no_stream

PROMPT_TEMPLATE = """
Given reference materials and questions, please determine if the reference materials and questions are relevant
reference materials:
{ref_doc}

Use the following format:

Question: the input question you must answer
Thought: you should always think about the reason.
Final Answer: {{"res": just judge if the reference materials and question are relevant, should be on of [related, unrelated, 相关, 不相关]}}, the answer must be json format, no additional replies allowed.

Begin!

Question: {user_request}"""


class SSLLM:
    def __init__(self, llm=None):
        self.llm = llm

    def run(self, line, query):
        """
        Input: one line
        Output: the relative text
        """
        content = line['raw']
        if isinstance(content, str):
            content = content.split('\n')

        res = []
        for page in content:
            rel_text = self.filter_section(page, query)
            if rel_text:
                res.append(rel_text)
        return RefMaterial(url=line['url'], text=res).to_dict()

    def filter_section(self, page, query):
        if isinstance(page, str):
            text = page
        elif isinstance(page, dict):
            # text = page['related_questions']
            text = page['page_content']
        else:
            print(type(page))
            raise TypeError
        prompt = PROMPT_TEMPLATE.format(
            ref_doc=text,
            user_request=query,
        )
        if self.llm:
            res = self.llm.chat(prompt, stream=False)
        else:
            res = qwen_chat_no_stream(prompt)
        print(res)
        if 'Final Answer:' in res:
            fa = res.split('Final Answer:')[-1].strip()
            try:
                fa = json.loads(fa)
                answer = fa['res']
            except Exception as ex:
                print(ex)
                answer = fa
            if answer == 'related' or answer == '相关':
                print(res)
                return text
            else:
                return ''
        return ''
