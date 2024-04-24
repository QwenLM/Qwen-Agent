import pytest

from qwen_agent.agents import ArticleAgent


@pytest.mark.skip()
def test_article_agent_full_article():
    llm_cfg = {'model': 'qwen-max', 'api_key': '', 'model_server': 'dashscope'}
    agent = ArticleAgent(llm=llm_cfg)
    messages = [{
        'role': 'user',
        'content': [{
            'text': 'Qwen-Agent简介'
        }, {
            'file': 'https://github.com/QwenLM/Qwen-Agent'
        }]
    }]
    *_, last = agent.run(messages, full_article=True)

    assert last[-2]['content'] == '>\n> Writing Text: \n'
    assert len(last[-1]['content']) > 0
