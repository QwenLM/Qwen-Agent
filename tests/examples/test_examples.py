import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(__file__, '../../..')))  # noqa

ROOT_RESOURCE = os.path.abspath(os.path.join(__file__, '../../../examples/resource'))  # noqa
from examples.assistant_add_custom_tool import test as assistant_add_custom_tool  # noqa
from examples.assistant_angry_girlfriend import test as assistant_angry_girlfriend  # noqa
# from examples.assistant_doctor import test as assistant_doctor
from examples.assistant_growing_girl import test as assistant_growing_girl  # noqa
from examples.assistant_weather_bot import test as assistant_weather_bot  # noqa
from examples.function_calling import test as function_calling  # noqa
# from examples.gpt_mentions import test as gpt_mentions  # noqa
from examples.group_chat_chess import test as group_chat_chess  # noqa
from examples.group_chat_demo import test as group_chat_demo  # noqa
from examples.llm_riddles import test as llm_riddles  # noqa
from examples.llm_vl_mix_text import test as llm_vl_mix_text  # noqa
from examples.multi_agent_router import test as multi_agent_router  # noqa
from examples.react_data_analysis import test as react_data_analysis  # noqa
from examples.visual_storytelling import test as visual_storytelling  # noqa


@pytest.mark.parametrize('query', ['draw a dog'])
def test_assistant_add_custom_tool(query):
    assistant_add_custom_tool(query=query)


@pytest.mark.parametrize('query', ['海淀区天气'])
@pytest.mark.parametrize('file', [None, os.path.join(ROOT_RESOURCE, 'poem.pdf')])
def test_assistant_weather_bot(query, file):
    assistant_weather_bot(query=query, file=file)


@pytest.mark.parametrize('query', ['你今天真好看'])
def test_assistant_angry_girlfriend(query):
    assistant_angry_girlfriend(query=query)


# @pytest.mark.parametrize('query', ['医生，可以帮我看看我是否健康吗？'])
# @pytest.mark.parametrize('file', [
#     None,
#     'https://pic4.zhimg.com/80/v2-2c8eedf3e12386fedcd5589cf5575717_720w.webp'
# ])
# def test_assistant_doctor(query, file):
#     assistant_doctor(query=query, file=file)


@pytest.mark.parametrize('query', ['请用image_gen开始创作！'])
@pytest.mark.parametrize('file', [None, os.path.join(ROOT_RESOURCE, 'growing_girl.pdf')])
def test_assistant_growing_girl(query, file):
    assistant_growing_girl(query=query, file=file)


def test_llm_vl_mix_text():
    llm_vl_mix_text()


@pytest.mark.parametrize('query', [None, '看图说话'])
@pytest.mark.parametrize('image', ['https://img01.sc115.com/uploads3/sc/vector/201809/51413-20180914205509.jpg'])
def test_visual_storytelling(query, image):
    visual_storytelling(query=query, image=image)


def test_function_calling():
    function_calling()


# @pytest.mark.parametrize('history', ['你能做什么？'])
# @pytest.mark.parametrize('chosen_plug',
#                          ['code_interpreter', 'doc_qa', 'assistant'])
# def test_gpt_mentions(history, chosen_plug):
#     gpt_mentions(history=history, chosen_plug=chosen_plug)


@pytest.mark.parametrize(
    'query', ['pd.head the file first and then help me draw a line chart to show the changes in stock prices'])
@pytest.mark.parametrize('file', [os.path.join(ROOT_RESOURCE, 'stock_prices.csv')])
def test_react_data_analysis(query, file):
    react_data_analysis(query=query, file=file)


def test_llm_riddles():
    llm_riddles()


@pytest.mark.parametrize('query', ['告诉我你现在知道什么了'])
@pytest.mark.parametrize('image', [None, 'https://img01.sc115.com/uploads/sc/jpgs/1505/apic11540_sc115.com.jpg'])
@pytest.mark.parametrize('file', [None, os.path.join(ROOT_RESOURCE, 'poem.pdf')])
def test_multi_agent_router(query, image, file):
    multi_agent_router(query=query, image=image, file=file)


@pytest.mark.parametrize('query', ['开始吧'])
def test_group_chat_chess(query):
    group_chat_chess(query=query)


def test_group_chat_demo():
    group_chat_demo()
