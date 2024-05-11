from qwen_agent.agents.doc_qa import BasicDocQA
from qwen_agent.gui import WebUI


def test():
    bot = BasicDocQA(llm={'model': 'qwen-plus'})
    messages = [{'role': 'user', 'content': [{'text': '介绍图一'}, {'file': 'https://arxiv.org/pdf/1706.03762.pdf'}]}]
    for rsp in bot.run(messages):
        print(rsp)


def app_gui():
    # Define the agent
    bot = BasicDocQA(llm={'model': 'qwen-plus'})
    chatbot_config = {
        'prompt.suggestions': [
            {
                'text': '介绍图一'
            },
            {
                'text': '第二章第一句话是什么？'
            },
        ]
    }
    WebUI(bot, chatbot_config=chatbot_config).run()


if __name__ == '__main__':
    # test()
    app_gui()
