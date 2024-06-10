# LLM 介绍

本文档介绍了LLM类的使用和开发流程。

## 1. LLM 使用

目前，Qwen-Agent提供了Qwen的DashScope API和OpenAI API访问接口；Qwen-VL的DashScope API访问接口。均已经支持流式Function Calling。

### 1.1. 外部直接调用
LLM统一使用`get_chat_model(cfg: Optional[Dict] = None) -> BaseChatModel`接口来调用，参数传入LLM的配置文件，
配置文件格式如下：
- model_type: 对应某个具体的llm类，是llm类注册的名字，即唯一ID。使用内置的dashscope和OpenAI API时，可以省略这个参数。外部注册的LLM类，需要传入这个参数来指定。
- model：具体的模型名称
- model_server：模型服务地址
- generate_cfg：模型生成时候的参数

LLM类统一使用`llm.chat(...)`接口生成回复，支持输入消息列表、函数等参数，具体参数列表详见[BaseChatModel](../qwen_agent/llm/base.py)。
LLM完整使用样例见[Function Calling](../examples/function_calling.py)。
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

# 此处演示流式输出效果
responses = []
for responses in llm.chat(messages=messages,
                          functions=functions,
                          stream=True):
    print(responses)
```

### 1.2. Agent内部调用

在Agent中，使用`_call_llm(...)`函数调用LLM，每个Agent实例可以调用初始化给它的LLM，
`llm: Optional[Union[Dict, BaseChatModel]] = None`。支持的传入类型包括：：LLM配置文件或LLM对象。

注意，为了统一Agent的输出类型，Agent的`_call_llm(...)`接口默认使用流式生成方式访问LLM。

## 2. LLM 开发

Qwen-Agent提供了注册LLM的机制，在[LLM 基类](../qwen_agent/llm/base.py)中，实现了统一的`llm.chat(...)`接口，
新注册的LLM仅需要实现特有的三个函数：
- 非流式生成接口
- 流式生成接口（如果LLM本身不支持流式生成，可以将非流式结果封装成生成器返回）
- 工具调用接口

其中，如果新注册的LLM不支持工具调用，可以继承Qwen-Agent中实现的[BaseFnCallModel](../qwen_agent/llm/function_calling.py)类，
这个类通过封装一个类似ReAct的工具调用Prompt，已经基于普通对话接口实现了Function Calling。
