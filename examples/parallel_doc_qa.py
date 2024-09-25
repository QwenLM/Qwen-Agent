from qwen_agent.agents.doc_qa import ParallelDocQA
from qwen_agent.gui import WebUI


def test():
    bot = ParallelDocQA(llm={'model': 'qwen2.5-72b-instruct', 'generate_cfg': {'max_retries': 10}})
    messages = [
        {
            'role': 'user',
            'content': [
                {
                    'text': '介绍实验方法'
                },
                {
                    'file': 'https://arxiv.org/pdf/2310.08560.pdf'
                },
            ]
        },
    ]
    for rsp in bot.run(messages):
        print('bot response:', rsp)


def app_gui():
    # Define the agent
    bot = ParallelDocQA(
        llm={
            'model': 'qwen2.5-72b-instruct',
            'generate_cfg': {
                'max_retries': 10
            }
        },
        description='并行QA后用RAG召回内容并回答。支持文件类型：PDF/Word/PPT/TXT/HTML。使用与材料相同的语言提问会更好。',
    )

    chatbot_config = {'prompt.suggestions': [{'text': '介绍实验方法'}]}

    WebUI(bot, chatbot_config=chatbot_config).run()


if __name__ == '__main__':
    # test()
    app_gui()
