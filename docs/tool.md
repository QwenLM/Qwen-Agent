# Tool Introduction

This document introduces the usage and development process of the Tool class.

## 1. Tool Usage

### 1.1. Direct External Call
Tools uniformly utilize the `.call(params)` interface for calling, where you pass in the necessary parameters for the tool.
The tool then returns the results after execution, with the return type being `Union[str, list, dict]`.

For example, to directly call a image generation tool:

```py
from qwen_agent.tools import ImageGen

tool = ImageGen()
res = tool.call(params = {'prompt': 'a cute cat'})
print(res)
```

### 1.2. Internal call by Agent

In the Agent, the `_call_tool(...)` function is used to call tools, with each Agent instance capable of calling the tools that were initialized and assigned to it.
The tools can be passed in through `function_list: Optional[List[Union[str, Dict, BaseTool]]] = None` parameter.
The supported input types include the tool name, tool configuration file, or the tool object itself.
For instance, you can use `code_interpreter`, `{'name': 'code_interpreter', 'timeout': 10}`, or `CodeInterpreter()`.

Note that for the convenience of inputting tool results into LLMs, the Agent’s `_call_tool(...)` interface converts all returned results from the tools into string type. For more details, see the [Agent class](../qwen_agent/agent.py).

## 2. Tool Development

Qwen-Agent provides a mechanism for registering tools. For example, to register your own image generation tool:
- Specify the tool’s name, description, and parameters. Note that the string passed to `@register_tool('my_image_gen')` is automatically added as the `.name` attribute of the class and will serve as the unique identifier for the tool.
- Implement the `call(...)` function.

```py
import urllib.parse
import json5
import json
from qwen_agent.tools.base import BaseTool, register_tool
# Add a custom tool named my_image_gen：
@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    description = 'AI painting (image generation) service, input text description, and return the image URL drawn based on text information.'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description':
        'Detailed description of the desired image content, in English',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)
```

Once the tools are registered, they can be used as mentioned above.

If you prefer not to use the registration method, you can also directly define a tool class and then pass the tool object to the Agent (unregistered tools do not support passing the tool name or configuration file).

```py
import urllib.parse
import json5
import json
from qwen_agent.tools.base import BaseTool

class MyImageGen(BaseTool):
    name = 'my_image_gen'
    description = 'AI painting (image generation) service, input text description, and return the image URL drawn based on text information.'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description':
        'Detailed description of the desired image content, in English',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)
```
