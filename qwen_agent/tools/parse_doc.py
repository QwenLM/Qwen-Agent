import re


def parse_pdf_pypdf(path, pre_gen_question=False):
    from langchain.document_loaders import PyPDFLoader

    loader = PyPDFLoader(path)
    pages = loader.load_and_split()
    res = [{
        'page_content': page.page_content,
        'metadata': page.metadata
    } for page in pages]
    return res


def pre_process_html(s):
    # replace multiple newlines
    s = re.sub('\n+', '\n', s)
    # replace special string
    s = s.replace("Add to Qwen's Reading List", '')
    return s


def parse_html_bs(path, pre_gen_question=False):
    from langchain.document_loaders import BSHTMLLoader

    loader = BSHTMLLoader(path, open_encoding='utf-8')
    pages = loader.load_and_split()
    res = [{
        'page_content': pre_process_html(page.page_content),
        'metadata': page.metadata
    } for page in pages]
    return res
