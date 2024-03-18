# Tool 介绍

本文档介绍了Tool类的使用和开发流程。

## 1. Tool 使用

### 1.1. 外部直接调用
Tool统一使用`.call(params)`接口来调用，传入工具需要的参数，返回工具执行后的结果，返回的类型为`Union[str, list, dict]`。

例如，直接调用天气查询工具：
```py
from qwen_agent.tools import AmapWeather

tool = AmapWeather()
res = tool.call(params = {'location': '海淀区'})
print(res)
```

### 1.2. Agent内部调用

在Agent中，使用`_call_tool(...)`函数调用工具，每个Agent实例可以调用初始化给它的工具列表
`function_list: Optional[List[Union[str, Dict, BaseTool]]] = None`中的工具。
支持的传入类型包括：工具名、工具配置文件、或工具对象。例如`code_interpreter`、 `{'name': 'code_interpreter', 'timeout': 10}`、 或`CodeInterpreter()`。

注意，为了方便将工具结果输入LLM，Agent的`_call_tool(...)`接口会将所有工具返回的结果转为str类型，具体见[Agent类](../qwen_agent/agent.py)。

## 2. Tool 开发
Qwen-Agent提供了注册工具的机制，例如，下面我们注册一个自己的图片生成工具：
- 指定工具的name、description、和parameters，注意@register_tool('my_image_gen')中的'my_image_gen'会被自动添加为这个类的.name属性，将作为工具的唯一标识。
- 实现`call(...)`函数

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

注册好的工具，就可以按照上文直接使用或添加到Agent里使用了。

如果不想使用注册方式，也可以直接定义工具类，然后传工具对象给Agent（没有注册的工具，不支持传工具名或配置文件）。
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
