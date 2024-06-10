from qwen_agent.agents.doc_qa import ParallelDocQA


def test_parallel_qa():
    llm_cfg = {'model': 'qwen-max', 'api_key': '', 'model_server': 'dashscope'}
    agent = ParallelDocQA(llm=llm_cfg)
    messages = [{
        'role':
            'user',
        'content': [{
            'text': 'FastAPI适合IO密集任务吗'
        }, {
            'file': 'https://www.runoob.com/fastapi/fastapi-tutorial.html'
        }, {
            'file': 'https://www.runoob.com/fastapi/fastapi-install.html'
        }]
    }]
    *_, last = agent.run(messages)

    assert len(last[-1]['content']) > 0
