from qwen_agent.agents.doc_qa import BasicDocQA


def test_doc_qa():
    llm_cfg = {'model': 'qwen-max', 'api_key': '', 'model_server': 'dashscope'}
    agent = BasicDocQA(llm=llm_cfg)
    messages = [{
        'role': 'user',
        'content': [{
            'text': 'Summarize a title'
        }, {
            'file': 'https://www.runoob.com/fastapi/fastapi-tutorial.html'
        }]
    }]
    *_, last = agent.run(messages)

    assert len(last[-1]['content']) > 0
