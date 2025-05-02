"""An agent implemented by assistant with qwen3"""

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
from qwen_agent.utils.output_beautify import typewriter_print


def init_agent_service():
    llm_cfg = {
        'model': 'qwen3-235b-a22b',
        'model_type': 'qwen_dashscope',

        # 'generate_cfg': {
        #     # Add: When the content is `<think>this is the thought</think>this is the answer`
        #     # Do not add: When the response has been separated by reasoning_content and content
        #     # This parameter will affect the parsing strategy of tool call
        #     # 'thought_in_content': True,
        #
        #     # When using the Dash Scope API, pass the parameter of whether to enable thinking mode in this way
        #     'enable_thinking': False,
        #
        #     # When using OAI API, pass the parameter of whether to enable thinking mode in this way
        #     # 'extra_body': {
        #     #     'enable_thinking': False
        #     # }
        # },
    }
    tools = [
        {
            'mcpServers': {  # You can specify the MCP configuration file
                'time': {
                    'command': 'uvx',
                    'args': ['mcp-server-time', '--local-timezone=Asia/Shanghai']
                },
                'fetch': {
                    'command': 'uvx',
                    'args': ['mcp-server-fetch']
                }
            }
        },
        'code_interpreter',  # Built-in tools
    ]
    bot = Assistant(llm=llm_cfg,
                    function_list=tools,
                    name='Qwen3 Tool-calling Demo',
                    description="I'm a demo using the Qwen3 tool calling. Welcome to add and play with your own tools!")

    return bot


def test(query: str = 'What time is it?'):
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
    chatbot_config = {
        'prompt.suggestions': [
            'What time is it?',
            'https://github.com/orgs/QwenLM/repositories Extract markdown content of this page, then draw a bar chart to display the number of stars.'
        ]
    }
    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
