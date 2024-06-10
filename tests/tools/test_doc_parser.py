from qwen_agent.tools import DocParser


def test_doc_parser():
    tool = DocParser()
    res = tool.call({'url': 'https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf'})
    print(res)


if __name__ == '__main__':
    test_doc_parser()
