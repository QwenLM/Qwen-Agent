import pytest

from qwen_agent.agents import DocQAAgent


@pytest.mark.skip()
def test_doc_qa():
    llm_cfg = {
        'model': 'qwen-plus',
        'api_key': '',
        'model_server': 'dashscope'
    }
    agent = DocQAAgent(llm=llm_cfg)
    messages = [{
        'role':
        'user',
        'content': [{
            'text': 'How to install'
        }, {
            'file': 'https://github.com/QwenLM/Qwen-Agent'
        }]
    }]
    *_, last = agent.run(messages)

    assert len(last[-1]['content']) > 0
