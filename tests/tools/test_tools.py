import json

import pytest

from qwen_agent.tools import AmapWeather, CodeInterpreter, DocParser, ImageGen, Retrieval, SimilaritySearch, Storage


# [NOTE] 不带“市”会出错
@pytest.mark.parametrize('params', [json.dumps({'location': '北京市'}), {'location': '杭州市'}])
def test_amap_weather(params):
    tool = AmapWeather()
    tool.call(params)


def test_code_interpreter():
    tool = CodeInterpreter()
    tool.call("print('hello qwen')")


def test_doc_parser():
    tool = DocParser()
    tool.call({'url': 'https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf'})


def test_image_gen():
    tool = ImageGen()
    tool.call({'prompt': 'a dog'})


def test_retrieval():
    tool = Retrieval()
    tool.call({
        'query': 'Who are the authors of this paper?',
        'files': ['https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf']
    })


def test_similarity_search():
    tool = SimilaritySearch()
    doc = ('主要序列转导模型基于复杂的循环或卷积神经网络，包括编码器和解码器。性能最好的模型还通过注意力机制连接编码器和解码器。'
           '我们提出了一种新的简单网络架构——Transformer，它完全基于注意力机制，完全不需要递归和卷积。对两个机器翻译任务的实验表明，'
           '这些模型在质量上非常出色，同时具有更高的并行性，并且需要的训练时间显着减少。'
           '我们的模型在 WMT 2014 英语到德语翻译任务中取得了 28.4 BLEU，比现有的最佳结果（包括集成）提高了 2 BLEU 以上。'
           '在 WMT 2014 英法翻译任务中，我们的模型在 8 个 GPU 上训练 3.5 天后，建立了新的单模型最先进 BLEU 分数 41.0，'
           '这只是最佳模型训练成本的一小部分文献中的模型。')
    tool.call({'query': '这个模型要训练多久？'}, doc=doc)


@pytest.mark.parametrize('operate', ['put'])
def test_storage_put(operate):
    tool = Storage()
    tool.call({'operate': operate, 'key': '345/456/11', 'value': 'hello'})

    tool.call({'operate': operate, 'key': '/345/456/12', 'value': 'hello'})


@pytest.mark.parametrize('operate', ['scan'])
def test_storage_scan(operate):
    tool = Storage()
    tool.call({'operate': operate, 'key': '345/456/'})

    tool.call({'operate': operate, 'key': '/345/456'})


@pytest.mark.parametrize('operate', ['get', 'delete'])
def test_storage_get_delete(operate):
    tool = Storage()
    tool.call({'operate': operate, 'key': '345/456/11'})

    tool.call({'operate': operate, 'key': '/345/456/12'})
