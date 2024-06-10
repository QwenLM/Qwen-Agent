# LLM Introduction

This document introduces the usage and development process of LLM classes.

## 1. LLM Usage

Currently, Qwen-Agent provides access interfaces to Qwen's DashScope API and OpenAI API, and Qwen-VL's DashScope API. Both already support streaming Function Calling.

### 1.1. Direct External Call
The LLM is uniformly calling using the interface `get_chat_model(cfg: Optional[Dict] = None) -> BaseChatModel`, with parameters passed in being the configuration file for the LLM. The configuration file format is as follows:
- model_type: Corresponds to a specific LLM class, which is the registered name of the LLM class, i.e., the unique ID. This parameter can be omitted when using the built-in DashScope and OpenAI API. For externally registered LLM classes, this parameter must be provided to specify the class.
- model: The specific model name
- model_server: The model service address
- generate_cfg: The parameters for model generation

LLM classes uniformly use the `llm.chat(...)` interface to generate responses, supporting input of message lists, functions, and other parameters. For a detailed parameter list, see [BaseChatModel](../qwen_agent/llm/base.py).

See a complete example of LLM usage at [Function Calling](../examples/function_calling.py).

```py

from qwen_agent.llm import get_chat_model

llm_cfg = {
            # Use the model service provided by DashScope:
            # 'model_type': 'qwen_dashscope',
            'model': 'qwen-max',
            'model_server': 'dashscope',
            # Use your own model service compatible with OpenAI API:
            # 'model': 'Qwen',
            # 'model_server': 'http://127.0.0.1:7905/v1',
            # (Optional) LLM hyper-paramters:
            'generate_cfg': {
                'top_p': 0.8
            }
          }
llm = get_chat_model(llm_cfg)
messages = [{
    'role': 'user',
    'content': "What's the weather like in San Francisco?"
}]
functions = [{
    'name': 'get_current_weather',
    'description': 'Get the current weather in a given location',
    'parameters': {
        'type': 'object',
        'properties': {
            'location': {
                'type': 'string',
                'description':
                'The city and state, e.g. San Francisco, CA',
            },
            'unit': {
                'type': 'string',
                'enum': ['celsius', 'fahrenheit']
            },
        },
        'required': ['location'],
    },
}]

# The streaming output responses
responses = []
for responses in llm.chat(messages=messages,
                          functions=functions,
                          stream=True):
    print(responses)
```

### 1.2. Internal call by Agent

In the Agent, the `_call_llm(...)` function is used to call the LLM, and each Agent instance can call the LLM that was initialized for it,`llm: Optional[Union[Dict, BaseChatModel]] = None`.
The supported types include: LLM configuration file or LLM object.

Note that in order to maintain the consistency of output type in the Agent,
the Agent’s `_call_llm(...)` interface by default accesses the LLM using a streaming generation method.

## 2. LLM Development
Qwen-Agent provides a mechanism for registering LLMs. In the [LLM Base Class](../qwen_agent/llm/base.py), a uniform `llm.chat(...)` interface is implemented.
Newly registered LLMs only need to implement three specific functions:
- A non-streaming generation interface;
- A streaming generation interface (If the LLM itself does not support streaming generation, the non-streaming results can be wrapped into a generator for return);
- A function call interface.

If the newly registered LLM does not support function calls, it can inherit from the [BaseFnCallModel](../qwen_agent/llm/function_calling.py) class implemented in Qwen-Agent.
This class has implemented Function Calling based on the general conversational interface by wrapping a tool call Prompt similar to ReAct.
