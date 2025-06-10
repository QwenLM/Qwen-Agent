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

# Example: Calling Multiple Functions in Parallel
# Reference: https://platform.openai.com/docs/guides/function-calling
import json
import os

from qwen_agent.llm import get_chat_model


# Example dummy function hard coded to return the same weather
# In production, this could be your backend API or an external API
def get_current_weather(location, unit='fahrenheit'):
    """Get the current weather in a given location"""
    if 'tokyo' in location.lower():
        return json.dumps({'location': 'Tokyo', 'temperature': '10', 'unit': 'celsius'})
    elif 'san francisco' in location.lower():
        return json.dumps({'location': 'San Francisco', 'temperature': '72', 'unit': 'fahrenheit'})
    elif 'paris' in location.lower():
        return json.dumps({'location': 'Paris', 'temperature': '22', 'unit': 'celsius'})
    else:
        return json.dumps({'location': location, 'temperature': 'unknown'})


def test():
    llm = get_chat_model({
        # Use the model service provided by DashScope:
        # 'model': 'qwen2-72b-instruct',
        # 'model_server': 'dashscope',
        # 'api_key': os.getenv('DASHSCOPE_API_KEY'),

        # Use the OpenAI-compatible model service provided by DashScope:
        'model': 'qwen-plus-latest',
        'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'api_key': os.getenv('DASHSCOPE_API_KEY'),
        'generate_cfg': {
            'fncall_prompt_type': 'qwen'
        },
    })

    # Step 1: send the conversation and available functions to the model
    messages = [{
        'role': 'user',
        'content': "What's the weather like in San Francisco? And what about Tokyo? Paris?",
    }]
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
    for responses in llm.chat(
            messages=messages,
            functions=functions,
            stream=True,
            extra_generate_cfg=dict(
                # This will truncate the history until the input tokens are less than the limit.
                max_input_tokens=6500,

                # Note: set parallel_function_calls=True to enable parallel function calling
                parallel_function_calls=True,  # Default: False
                # Note: set function_choice='auto' to let the model decide whether to call a function or not
                # function_choice='auto',  # 'auto' is the default if function_choice is not set
                # Note: set function_choice='get_current_weather' to force the model to call this function
                # function_choice='get_current_weather',
            ),
    ):
        print(responses)

    messages.extend(responses)  # extend conversation with assistant's reply

    # Step 2: check if the model wanted to call a function
    fncall_msgs = [rsp for rsp in responses if rsp.get('function_call', None)]
    if fncall_msgs:
        # Note: the JSON response may not always be valid; be sure to handle errors
        available_functions = {
            'get_current_weather': get_current_weather,
        }  # only one function in this example, but you can have multiple

        for msg in fncall_msgs:
            # Step 3: call the function
            print('# Function Call:')
            function_name = msg['function_call']['name']
            function_to_call = available_functions[function_name]
            function_args = json.loads(msg['function_call']['arguments'])
            function_response = function_to_call(
                location=function_args.get('location'),
                unit=function_args.get('unit'),
            )
            print('# Function Response:')
            print(function_response)
            # Step 4: send the info for each function call and function response to the model
            # Note: please put the function results in the same order as the function calls
            messages.append({
                'role': 'function',
                'name': function_name,
                'content': function_response,
            })  # extend conversation with function response

        print('# Assistant Response 2:')
        for responses in llm.chat(
                messages=messages,
                functions=functions,
                extra_generate_cfg={
                    'max_input_tokens': 6500,
                    'parallel_function_calls': True,
                },
                stream=True,
        ):  # get a new response from the model where it can see the function response
            print(responses)


if __name__ == '__main__':
    test()
