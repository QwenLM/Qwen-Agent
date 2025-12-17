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

"""Example: Finance Assistant Bot using yfinance tool.

This example demonstrates how to use the Finance tool to build a stock analysis assistant.

Prerequisites:
    pip install yfinance

Usage:
    python assistant_finance_bot.py

You can ask questions like:
    - "What's the current price of AAPL?"
    - "Show me Tesla's stock history for the past 3 months"
    - "Give me financial information about Microsoft"
    - "Compare the PE ratios of GOOGL and META"
    - "What's Alibaba's market cap? (use 9988.HK or BABA)"
    - "What's Toyota's market info? (use 7203.T)"
"""

from qwen_agent.agents import Assistant
from qwen_agent.utils.output_beautify import typewriter_print
from qwen_agent.gui import WebUI

def main():
    # Step 1: Configure the LLM
    llm_cfg = {
        # Use DashScope model service:
        #'model': 'qwen-max-latest',
        #'model_type': 'qwen_dashscope',
        # 'api_key': 'YOUR_DASHSCOPE_API_KEY',  # Uses DASHSCOPE_API_KEY env var if not set

        # Or use OpenAI-compatible API (e.g., vLLM, Ollama):
        'model': 'Qwen3-Next-80B-A3B',
        'model_server': 'http://localhost:8080/', # local llama server
        'api_key': 'EMPTY',

        'generate_cfg': {
            'top_p': 0.8,
        }
    }

    # Step 2: Define the system message for the finance assistant
    system_message = '''You are a professional financial analyst assistant. You have access to real-time stock market data through the finance tool.

When users ask about stocks or financial data:
1. Use the finance tool to retrieve accurate, up-to-date information
2. Present the data in a clear, organized manner
3. Provide brief analysis or context when appropriate
4. If comparing multiple stocks, present the data in a comparable format

For stock symbols:
- US stocks: Use standard tickers (AAPL, GOOGL, MSFT, TSLA, etc.)
- Hong Kong stocks: Add .HK suffix (9988.HK for Alibaba HK)
- Chinese A-shares: Use .SS for Shanghai (600519.SS) or .SZ for Shenzhen (000001.SZ)
- Tokyo stocks: Add .T suffix (7203.T for Toyota Motor Japan)

Available actions for the finance tool:
- "price": Get current stock price and trading info
- "history": Get historical price data (specify period like "1mo", "3mo", "1y")
- "info": Get detailed company information
- "financials": Get financial statements summary

Always be helpful and explain financial terms when needed.'''

    # Step 3: Create the assistant with the finance tool
    tools = ['finance']
    bot = Assistant(
        llm=llm_cfg,
        system_message=system_message,
        function_list=tools,
    )

    # Step 4: Run the chatbot
    messages = []
    print('=' * 60)
    print('Finance Assistant Bot')
    print('=' * 60)
    print('Ask me about stocks, prices, company info, or financials!')
    print('Examples:')
    print('  - "What is Apple\'s current stock price?"')
    print('  - "Show me TSLA history for the past month"')
    print('  - "Tell me about Microsoft\'s financials"')
    print('Type "exit" to quit.')
    print('=' * 60)

    while True:
        query = input('\nYou: ').strip()
        if not query:
            continue
        if query.lower() in ['exit', 'quit', 'bye']:
            print('Goodbye!')
            break

        messages.append({'role': 'user', 'content': query})
        response = []
        response_plain_text = ''
        print('\nAssistant: ', end='', flush=True)
        for response in bot.run(messages=messages):
            response_plain_text = typewriter_print(response, response_plain_text)
        messages.extend(response)
        print()

def app_gui():
    llm_cfg = {
        # Use DashScope model service:
        #'model': 'qwen-max-latest',
        #'model_type': 'qwen_dashscope',
        # 'api_key': 'YOUR_DASHSCOPE_API_KEY',  # Uses DASHSCOPE_API_KEY env var if not set

        # Or use OpenAI-compatible API (e.g., vLLM, Ollama):
        'model': 'Qwen3-Next-80B-A3B',
        'model_server': 'http://localhost:8080/', # local llama server
        'api_key': 'EMPTY',

        'generate_cfg': {
            'top_p': 0.8,
        }
    }
    # Define the agent
    tools = ['finance']
    bot = Assistant(
        llm=llm_cfg,
    #    system_message=system_message,
        function_list=tools,
        name='Qwen3 finance Demo',
        description="I'm a demo using the Qwen3 tool finance",
    )

    chatbot_config = {
        'prompt.suggestions': [
            'What is Apple\'s current stock price?',
            'Show me TSLA history for the past month',
            'Tell me about Microsoft\'s financials',
            'トヨタ自動車の配当について教えてください。'
        ]
    }
    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()
    
if __name__ == '__main__':
    #main()
    app_gui()
