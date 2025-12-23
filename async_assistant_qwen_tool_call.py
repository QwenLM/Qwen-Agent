import os
import json
import asyncio
import aiohttp
import json5
from qwen_agent.agents import AsyncAssistant
from qwen_agent.tools.base import BaseTool, register_tool
import dotenv
dotenv.load_dotenv()

@register_tool('serper_scrape')
class SerperScrapeTool(BaseTool):
    description = 'Scrape webpage content using Serper API. Input: URL of the webpage. Output: JSON string with webpage content including text.'
    parameters = {
        'type': 'object',
        'properties': {
            'url': {
                'type': 'string',
                'description': 'The URL of the webpage to scrape',
            }
        },
        'required': ['url'],
    }

    async def call(self, params: str, **kwargs) -> str:
        """
        Call the tool with the given parameters (async version).

        Args:
            params: JSON string containing the parameters

        Returns:
            The webpage content as a JSON string
        """
        # Use BaseTool's _verify_json_format_args method
        params_dict = json5.loads(params)
        url = params_dict['url']
        api_url = "https://scrape.serper.dev/"

        payload = {
            "url": url
        }

        headers = {
            'X-API-KEY': os.getenv('SERPER_API_KEY'),
            'Content-Type': 'application/json'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as response:
                    response.raise_for_status()
                    result_json = await response.json()

            # Extract key information
            simplified = {
                'url': url,
                'text': result_json.get('text', ''),
            }

            return json.dumps(simplified, ensure_ascii=False)  
        except Exception as e:
            return json.dumps({
                'error': str(e),
                'url': url,
                'text': ''
            }, ensure_ascii=False)


# Configure the LLM for async mode
llm_cfg = {
        # Use your own model service compatible with OpenAI API by vLLM/SGLang:
        'model': 'Qwen/Qwen3-30B-A3B-Instruct-2507',
        'model_server': 'http://localhost:8000/v1',  # api_base
        'model_type': 'oai_async', # you can also comment here
        'api_key': 'EMPTY',
}

# Create an async assistant with the serper_scrape tool
system_instruction = '''You are a helpful assistant that can scrape web pages using the Serper API.
When the user provides a URL, use the serper_scrape tool to fetch and analyze the content.
Provide clear summaries of the scraped content.'''

tools = ['serper_scrape']  # Use the custom serper_scrape tool
bot = AsyncAssistant(
    llm=llm_cfg,
    system_message=system_instruction,
    function_list=tools
)


async def run_agent(query: str = 'Scrape https://qwen.readthedocs.io/en/latest/deployment/vllm.html'):
    """Run the async agent with a query"""
    messages = [{'role': 'user', 'content': query}]

    response = await bot.run(messages=messages)

    # Print the complete response
    for msg in response:
        if msg.get('role') == 'assistant' and msg.get('content'):
            print(msg['content'])

    print(f"Response: {response[-1]}")
    return response


if __name__ == '__main__':
    asyncio.run(run_agent())
