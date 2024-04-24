import os

import pytest

from qwen_agent.llm import get_chat_model


@pytest.mark.parametrize('cfg', [0, 1])
def test_function_content(cfg):
    if cfg == 0:
        llm = get_chat_model({
            # Use the model service provided by DashScope:
            'model': 'qwen-max',
            'model_server': 'dashscope',
            'api_key': os.getenv('DASHSCOPE_API_KEY'),
        })
    else:
        llm = get_chat_model({
            # Use the model service provided by Together.AI:
            'model': 'Qwen/Qwen1.5-14B-Chat',
            'model_server': 'https://api.together.xyz',  # api_base
            'api_key': os.getenv('TOGETHER_API_KEY'),
        })

    # Step 1: send the conversation and available functions to the model
    messages = [{'role': 'user', 'content': "What's the weather like in San Francisco?"}]
    functions = [{
        'name': 'get_current_weather',
        'description': 'Get the current weather in a given location',
        'parameters': {
            'type': 'object',
            'properties': {
                'location': {
                    'type': 'string',
                    'description': 'The city and state, e.g. San Francisco, CA',
                },
                'unit': {
                    'type': 'string',
                    'enum': ['celsius', 'fahrenheit']
                },
            },
            'required': ['location'],
        },
    }]

    print('# Assistant Response 1:')
    responses = []
    for responses in llm.chat(messages=messages, functions=functions, stream=True):
        print(responses)

    messages.extend(responses)  # extend conversation with assistant's reply

    # Step 2: check if the model wanted to call a function
    last_response = messages[-1]
    assert 'function_call' in last_response
    messages.append({
        'role': 'function',
        'name': last_response['function_call']['name'],
        'content': '',
    })

    print('# Assistant Response 2:')
    for responses in llm.chat(
            messages=messages,
            functions=functions,
            stream=True,
    ):  # get a new response from the model where it can see the function response
        print(responses)


if __name__ == '__main__':
    test_function_content(0)
    test_function_content(1)
