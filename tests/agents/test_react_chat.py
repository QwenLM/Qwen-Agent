import os
import shutil
from pathlib import Path

from qwen_agent.agents import ReActChat
from qwen_agent.llm.schema import ContentItem, Message


def test_react_chat():
    llm_cfg = {'model': 'qwen-max'}
    tools = ['image_gen', 'amap_weather']
    agent = ReActChat(llm=llm_cfg, function_list=tools)

    messages = [Message('user', '海淀区天气')]

    *_, last = agent.run(messages)

    assert '\nAction: ' in last[-1].content
    assert '\nAction Input: ' in last[-1].content
    assert '\nObservation: ' in last[-1].content
    assert '\nThought: ' in last[-1].content
    assert '\nFinal Answer: ' in last[-1].content


def test_react_chat_with_file():
    if os.path.exists('workspace'):
        shutil.rmtree('workspace')
    llm_cfg = {
        'model': 'qwen-max',
        'model_server': 'dashscope',
        'api_key': os.getenv('DASHSCOPE_API_KEY'),

        # 'model': 'Qwen/Qwen1.5-72B-Chat',
        # 'model_server': 'https://api.together.xyz',
        # 'api_key': os.getenv('TOGETHER_API_KEY'),
    }
    tools = ['code_interpreter']
    agent = ReActChat(llm=llm_cfg, function_list=tools)
    messages = [
        Message(
            'user',
            [
                ContentItem(
                    text=  # noqa
                    'pd.head the file first and then help me draw a line chart to show the changes in stock prices'),
                ContentItem(
                    file=str(Path(__file__).resolve().parent.parent.parent / 'examples/resource/stock_prices.csv'))
            ])
    ]

    *_, last = agent.run(messages)
    assert len(last[-1].content) > 0
