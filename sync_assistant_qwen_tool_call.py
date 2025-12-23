import os
import json
import requests
import json5
from qwen_agent.agents import Assistant
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

    def call(self, params: str, **kwargs) -> str:
        """
        Call the tool with the given parameters (sync version).

        Args:
            params: JSON string containing the parameters

        Returns:
            The webpage content as a JSON string
        """
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
            response = requests.post(api_url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            result_json = response.json()

            # Extract key information
            simplified = {
                'url': url,
                'text': result_json.get('text', ''),
            }

            if simplified['text'] == '':
                print(f"[DEBUG] Error: {url} returned no text")

            return json.dumps(simplified, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR SerperScrape] {url}: {type(e).__name__}: {str(e)}")
            return json.dumps({
                'error': str(e),
                'url': url,
                'text': ''
            }, ensure_ascii=False)


# Configure the LLM
llm_cfg = {
        # Use your own model service compatible with OpenAI API by vLLM/SGLang:
        'model': 'Qwen/Qwen3-30B-A3B-Instruct-2507',
        'model_server': 'http://localhost:8000/v1',  # api_base
        'api_key': 'EMPTY',
}

# Create a synchronous assistant with the serper_scrape tool
system_instruction = '''You are a helpful assistant that can scrape web pages using the Serper API.
When the user provides a URL, use the serper_scrape tool to fetch and analyze the content.
Provide clear summaries of the scraped content.'''

tools = ['serper_scrape']  # Use the custom serper_scrape tool
bot = Assistant(
    llm=llm_cfg,
    system_message=system_instruction,
    function_list=tools
)


def run_agent(query: str = 'Scrape https://qwen.readthedocs.io/en/latest/deployment/vllm.html#thinking-non-thinking-modes'):
    """Run the agent with a query"""
    messages = [{'role': 'user', 'content': query}]

    prev_response = []
    for response in bot.run(messages=messages):
        prev_response.append(response)
        

    print(f"\nFinal Response: {response}")
    return response


if __name__ == '__main__':
    run_agent()
