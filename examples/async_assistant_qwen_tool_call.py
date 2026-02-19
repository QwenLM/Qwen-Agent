"""
Before running this script, you need to install the async openai package and run the vllm server.
```bash
pip install async-openai
vllm serve Qwen/Qwen3-30B-A3B-Instruct-2507 
```
"""

import json
import asyncio
import json5
from qwen_agent.agents import AsyncAssistant
from qwen_agent.tools.base import BaseTool, register_tool

@register_tool('get_weather')
class GetWeatherTool(BaseTool):
    description = 'Get current weather information for a city. Input: city name. Output: weather information.'
    parameters = {
        'type': 'object',
        'properties': {
            'city': {
                'type': 'string',
                'description': 'The name of the city',
            }
        },
        'required': ['city'],
    }

    async def call(self, params: str, **kwargs) -> str:
        params_dict = json5.loads(params)
        city = params_dict['city']

        # Simple hardcoded weather data
        weather_info = {
            'city': city,
            'temperature': '22°C',
            'condition': 'Sunny',
            'humidity': '60%'
        }

        return json.dumps(weather_info, ensure_ascii=False)


# Configure the LLM for async mode
llm_cfg = {
        # Use your own model service compatible with OpenAI API by vLLM/SGLang:
        'model': 'Qwen/Qwen3-30B-A3B-Instruct-2507',
        'model_server': 'http://localhost:8000/v1',  # api_base
        'model_type': 'oai_async', # you can also comment here
        'api_key': 'EMPTY',
}

# Create an async assistant with the get_weather tool
system_instruction = '''You are a helpful assistant that can get weather information.
When the user asks about weather, use the get_weather tool.'''

tools = ['get_weather']
bot = AsyncAssistant(
    llm=llm_cfg,
    system_message=system_instruction,
    function_list=tools
)


async def run_agent(query: str = 'What is the weather in Beijing?'):
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
