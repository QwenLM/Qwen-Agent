import re

import html2text

from qwen_agent.actions import Simple


def gen_q(text):
    agent = Simple(stream=False)
    query = '根据参考资料提几个最合适的问题，问题答案可以在参考资料中找出'
    res = agent.run(text, query)
    return res


def parse_pdf_pypdf(path, pre_gen_question=False):
    from langchain.document_loaders import PyPDFLoader
    loader = PyPDFLoader(path)
    pages = loader.load_and_split()
    # print(pages)
    if pre_gen_question:
        res = []
        for page in pages:
            print(len(page.page_content.split(' ')))
            res.append({'page_content': page.page_content, 'metadata': page.metadata, 'related_questions': gen_q(page.page_content)})
    else:
        res = [{'page_content': page.page_content, 'metadata': page.metadata} for page in pages]

    return res


def parse_html(htmltext):
    return html2text.html2text(htmltext)


def replace_multiple_newlines(s):
    return re.sub('\n+', '\n', s)


def parse_html_bs(path, pre_gen_question=False):
    from langchain.document_loaders import BSHTMLLoader
    loader = BSHTMLLoader(path, open_encoding='utf-8')
    pages = loader.load_and_split()

    if pre_gen_question:
        res = []
        for page in pages:
            print(len(page.page_content.split(' ')))
            res.append({'page_content': replace_multiple_newlines(page.page_content), 'metadata': page.metadata, 'related_questions': gen_q(page.page_content)})
    else:
        res = [{'page_content': replace_multiple_newlines(page.page_content), 'metadata': page.metadata} for page in pages]

    return res
