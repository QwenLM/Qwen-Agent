# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A free web search assistant powered by free-web-search-ultimate MCP server.

This example demonstrates how to use the free-web-search-ultimate MCP server
with Qwen-Agent to enable real-time, privacy-first web search — no API keys
required.

Install the MCP server::

    pip install free-web-search-ultimate

Start the MCP server (required before running this script)::

    free-web-search-mcp

GitHub: https://github.com/wd041216-bit/free-web-search-ultimate
"""
import os
from typing import Optional

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI


def init_agent_service() -> Assistant:
    """Initialize the Qwen-Agent assistant with web search capability.

    Returns:
        An Assistant instance configured with the free-web-search MCP server.
    """
    llm_cfg = {
        "model": "qwen-max",
        "api_key": os.environ.get("DASHSCOPE_API_KEY", ""),
    }
    system = (
        "You are a helpful research assistant with access to real-time web search. "
        "Use the web search tool to find up-to-date information when needed. "
        "Always cite your sources and provide accurate, current information."
    )
    # Use free-web-search-ultimate MCP server — zero cost, no API key needed
    tools = [
        {
            "mcpServers": {
                "free-web-search": {
                    "command": "free-web-search-mcp",
                    "args": [],
                }
            }
        }
    ]
    bot = Assistant(
        llm=llm_cfg,
        name="Web Search Assistant",
        description="A research assistant with real-time web search capability",
        system_message=system,
        function_list=tools,
    )
    return bot


def test(query: str = "What are the latest developments in AI in 2025?") -> None:
    """Run a single query test.

    Args:
        query: The question to ask the assistant.
    """
    bot = init_agent_service()
    messages = [{"role": "user", "content": query}]
    for response in bot.run(messages):
        print("bot response:", response)


def app_tui() -> None:
    """Run the assistant in terminal UI mode."""
    bot = init_agent_service()
    messages = []
    print("Web Search Assistant (powered by free-web-search-ultimate)")
    print("Type your question and press Enter. The assistant will search the web for you.")
    print("-" * 60)
    while True:
        query = input("User: ").strip()
        if not query:
            print("Please enter a question.")
            continue
        messages.append({"role": "user", "content": query})
        response = []
        for response in bot.run(messages):
            print("Assistant:", response)
        messages.extend(response)


def app_gui() -> None:
    """Run the assistant with a web-based GUI."""
    bot = init_agent_service()
    chatbot_config = {
        "prompt.suggestions": [
            "What are the latest AI news today?",
            "Search for recent breakthroughs in quantum computing",
            "Find information about the current stock market trends",
            "What happened in the world this week?",
            "Search for the best Python libraries for data science in 2025",
        ]
    }
    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()


if __name__ == "__main__":
    # Uncomment the mode you want to run:
    # test()       # Single query test
    # app_tui()    # Terminal UI
    app_gui()      # Web GUI (default)
