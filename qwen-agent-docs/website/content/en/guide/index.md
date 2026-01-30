# Qwen-Agent Overview

Qwen-Agent is a framework for developing LLM applications based on the instruction following, tool usage, planning, and memory capabilities of Qwen.

## Chat with an Agent

```python
from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
from qwen_agent.utils.output_beautify import typewriter_print

# Define llm config
llm_cfg = {
    'model': 'qwen3-max',
    'model_type': 'qwen_dashscope',
}
# Define tools
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
    'image_gen',  # Built-in example tools
]
# Define agent
bot = Assistant(llm=llm_cfg,
                function_list=tools,
                name='Qwen3 Tool-calling Demo',
                description="I'm a demo using the Qwen3 tool calling. Welcome to add and play with your own tools!")

# === Chat ===
messages = [{'role': 'user', 'content': 'draw a cute dog'}]
response_plain_text = ''
for response in bot.run(messages=messages):
    response_plain_text = typewriter_print(response, response_plain_text)

# === Chat on GUI ===
chatbot_config = {
    'prompt.suggestions': [
        'draw a cute dog'
    ]
}
WebUI(
    bot,
    chatbot_config=chatbot_config,
).run()
```

See the [Installation instructions](./get_started/install.md) and [Quickstart guide](./get_started/quickstart.md) to get started building your own agents and applications with Qwen-Agent.
