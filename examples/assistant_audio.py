from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI


def test():
    bot = Assistant(llm={'model_type': 'qwenaudio_dashscope', 'model': 'qwen-audio-turbo-latest'})
    messages = [{
        'role':
            'user',
        'content': [{
            'audio': 'https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3'
        }, {
            'text': '这段音频在说什么?'
        }]
    }]
    for rsp in bot.run(messages):
        print(rsp)


def app_gui():
    # Define the agent
    bot = Assistant(llm={'model': 'qwen-audio-turbo-latest'})
    WebUI(bot).run()


if __name__ == '__main__':
    # test()
    app_gui()
