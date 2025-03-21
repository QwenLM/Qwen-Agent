"""An image generation agent implemented by assistant with qwq"""

import os

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
from qwen_agent.utils.output_beautify import typewriter_print

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')


def init_agent_service():
    llm_cfg = {
        'model': 'qwq-32b',
        'model_type': 'qwen_dashscope',
        'generate_cfg': {
            'fncall_prompt_type': 'nous'
        },
    }
    tools = [
        'image_gen',
        # 'web_search',  # Apply for an apikey here (https://serper.dev) and set it as an environment variable by `export SERPER_API_KEY=xxxxxx`
    ]
    bot = Assistant(
        llm=llm_cfg,
        function_list=tools,
        name='QwQ-32B Tool-calling Demo',
        description="I'm a demo using the QwQ-32B tool calling. Welcome to add and play with your own tools!")

    return bot


def test(query: str = '画一只猫，再画一只狗，最后画他们一起玩的画面，给我三张图'):
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = [{'role': 'user', 'content': query}]
    response_plain_text = ''
    for response in bot.run(messages=messages):
        response_plain_text = typewriter_print(response, response_plain_text)


def app_tui():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []
    while True:
        query = input('user question: ')
        messages.append({'role': 'user', 'content': query})
        response = []
        response_plain_text = ''
        for response in bot.run(messages=messages):
            response_plain_text = typewriter_print(response, response_plain_text)
        messages.extend(response)


def app_gui():
    # Define the agent
    bot = init_agent_service()
    chatbot_config = {'prompt.suggestions': ['画一只猫，再画一只狗，最后画他们一起玩的画面，给我三张图']}
    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
