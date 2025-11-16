# Day 7: Custom Tools - Building Your Own AI Superpowers

## 📚 Overview

Custom tools are the **abilities you give to your AI agents**. They transform your agent from a conversationalist into a doer.

**Examples:**
- 🌤️ Weather tool → Agent checks real weather
- 🧮 Calculator tool → Agent performs exact math
- 🗄️ Database tool → Agent queries your data
- 🎨 Image tool → Agent generates images

## 🎯 Learning Objectives

By the end of this day, you will:

1. **Master @register_tool decorator** - Register tools globally
2. **Define parameter schemas** - JSON Schema for tool inputs
3. **Handle json5 parsing** - Gracefully parse LLM-generated arguments
4. **Understand the tool registry** - How Qwen-Agent manages tools
5. **Build real-world tools** - Image generation, data processing
6. **Implement stateful tools** - Tools that remember state
7. **Test tools effectively** - Unit and integration testing
8. **Apply advanced patterns** - Async tools, error handling

## 🔑 Core Concepts

### The BaseTool Structure

Every tool inherits from `BaseTool`:

```python
class BaseTool:
    name: str                    # Tool identifier
    description: str             # What it does (shown to LLM)
    parameters: List[Dict]       # What inputs it needs (JSON Schema)

    def call(self, params: str, **kwargs) -> str:
        # Your implementation
        pass
```

**Think of it as:**
- `name` = Tool's ID badge
- `description` = Job description (teaches LLM when to use it)
- `parameters` = Instruction manual
- `call()` = Pressing the "RUN" button

## 🚀 Quick Start: Your First Custom Tool

```python
from qwen_agent.tools.base import BaseTool, register_tool
import json5

@register_tool('simple_calculator')
class SimpleCalculator(BaseTool):
    """A simple calculator that adds two numbers"""

    description = 'Adds two numbers together'

    parameters = [
        {
            'name': 'a',
            'type': 'number',
            'description': 'First number',
            'required': True
        },
        {
            'name': 'b',
            'type': 'number',
            'description': 'Second number',
            'required': True
        }
    ]

    def call(self, params: str, **kwargs) -> str:
        args = json5.loads(params)
        result = args['a'] + args['b']
        return f"The sum is {result}"

# Use with an agent
from qwen_agent.agents import Assistant

bot = Assistant(
    llm=llm_cfg,
    function_list=['simple_calculator']  # Use by name!
)
```

## 📖 The @register_tool Decorator

### What It Does

```python
@register_tool('my_tool')  # String becomes tool.name
class MyTool(BaseTool):
    pass
```

1. ✅ Registers tool globally in TOOL_REGISTRY
2. ✅ Sets the tool's `name` attribute
3. ✅ Makes it available by string name to agents

### Three Ways to Use Tools

```python
# Method 1: By name (must be registered)
Assistant(function_list=['my_tool'])

# Method 2: By class (no registration needed)
Assistant(function_list=[MyToolClass])

# Method 3: By instance (for configured tools)
Assistant(function_list=[MyTool(config='value')])

# Method 4: Mix and match!
Assistant(function_list=[
    'code_interpreter',    # Built-in by name
    MyTool,                # Custom by class
    ConfiguredTool(x=10)   # Custom by instance
])
```

## 🔧 JSON Schema Parameter Types

### Basic Types

```python
# String
{'name': 'message', 'type': 'string', 'description': 'Text message'}

# Number (int or float)
{'name': 'value', 'type': 'number', 'description': 'Numeric value'}

# Integer (whole numbers only)
{'name': 'count', 'type': 'integer', 'description': 'Item count'}

# Boolean
{'name': 'active', 'type': 'boolean', 'description': 'Is active?'}

# Array
{'name': 'items', 'type': 'array', 'description': 'List of items'}

# Object (nested)
{'name': 'config', 'type': 'object', 'description': 'Configuration'}
```

### Advanced: Enums

Restrict to specific values:

```python
{
    'name': 'unit',
    'type': 'string',
    'enum': ['celsius', 'fahrenheit', 'kelvin'],  # Only these!
    'description': 'Temperature unit'
}
```

### Advanced: Arrays with Item Schema

```python
{
    'name': 'numbers',
    'type': 'array',
    'description': 'List of numbers',
    'items': {'type': 'number'},  # Each item must be a number
    'required': True
}
```

### Advanced: Nested Objects

```python
{
    'name': 'filters',
    'type': 'object',
    'description': 'Query filters',
    'properties': {
        'age': {'type': 'integer'},
        'city': {'type': 'string'},
        'active': {'type': 'boolean'}
    },
    'required': False
}
```

## 💡 Why json5 Instead of json?

**LLMs sometimes generate imperfect JSON:**

```python
import json
import json5

# These all FAIL with json but WORK with json5:
"{key: 'value'}"        # Single quotes
'{number: 42}'          # Unquoted key
'{"a": 1, "b": 2,}'     # Trailing comma
'{/* comment */ x: 10}' # With comment

# Always use json5 in your tools!
def call(self, params: str, **kwargs):
    args = json5.loads(params)  # ✅ Forgiving
    # args = json.loads(params)  # ❌ Might fail
```

## 🌟 Real-World Tool Examples

### Example 1: Weather API

```python
@register_tool('weather_api')
class WeatherAPI(BaseTool):
    description = 'Get current weather for a city'

    parameters = [{
        'name': 'city',
        'type': 'string',
        'description': 'City name',
        'required': True
    }, {
        'name': 'units',
        'type': 'string',
        'enum': ['celsius', 'fahrenheit'],
        'required': False
    }]

    def call(self, params: str, **kwargs) -> str:
        args = json5.loads(params)
        city = args['city']
        units = args.get('units', 'celsius')

        # Call real weather API here
        temp = 22 if units == 'celsius' else 72

        return json.dumps({
            'city': city,
            'temperature': temp,
            'units': units,
            'condition': 'Sunny'
        })
```

### Example 2: Image Generation (from Official Examples)

```python
import urllib.parse

@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    description = 'AI painting service - generates images from text descriptions'

    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': 'Detailed description of desired image, in English',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)

        return json.dumps({
            'image_url': f'https://image.pollinations.ai/prompt/{prompt}'
        }, ensure_ascii=False)
```

### Example 3: Database Query

```python
@register_tool('db_query')
class DatabaseQuery(BaseTool):
    description = 'Query database with filters'

    parameters = [{
        'name': 'table',
        'type': 'string',
        'description': 'Table name',
        'required': True
    }, {
        'name': 'filters',
        'type': 'object',
        'properties': {
            'age': {'type': 'integer'},
            'city': {'type': 'string'}
        },
        'required': False
    }]

    def call(self, params: str, **kwargs) -> str:
        args = json5.loads(params)
        # Execute query (mock implementation)
        query = f"SELECT * FROM {args['table']}"
        if 'filters' in args:
            conditions = [f"{k}={v}" for k, v in args['filters'].items()]
            query += " WHERE " + " AND ".join(conditions)

        return json.dumps({'query': query, 'count': 10})
```

## 🔄 Stateful Tools

Tools that remember information between calls:

```python
@register_tool('counter')
class Counter(BaseTool):
    description = 'A counter that can increment, decrement, or reset'

    parameters = [{
        'name': 'action',
        'type': 'string',
        'enum': ['increment', 'decrement', 'reset', 'get'],
        'required': True
    }]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0  # State variable!

    def call(self, params: str, **kwargs) -> str:
        action = json5.loads(params)['action']

        if action == 'increment':
            self.count += 1
        elif action == 'decrement':
            self.count -= 1
        elif action == 'reset':
            self.count = 0

        return f"Count is now {self.count}"
```

**⚠️ Important:** Stateful tools need careful management in multi-user scenarios!

## 🧪 Testing Strategies

### Strategy 1: Direct Unit Testing

```python
def test_calculator():
    tool = SimpleCalculator()

    # Test normal case
    result = tool.call('{"a": 10, "b": 5}')
    assert "15" in result

    # Test negative numbers
    result = tool.call('{"a": -5, "b": 10}')
    assert "5" in result

    # Test floats
    result = tool.call('{"a": 1.5, "b": 2.5}')
    assert "4" in result

    print("✅ All tests passed!")
```

### Strategy 2: Integration Testing with Agents

```python
def test_with_agent():
    agent = Assistant(
        llm=llm_cfg,
        function_list=['simple_calculator']
    )

    messages = [{'role': 'user', 'content': 'What is 25 + 17?'}]

    # Check tool was called
    for response in agent.run(messages):
        tool_called = any(
            msg.get('function_call', {}).get('name') == 'simple_calculator'
            for msg in response
        )

    assert tool_called, "Tool was not called"
    print("✅ Integration test passed!")
```

## 📊 Tool Registry

### View All Registered Tools

```python
from qwen_agent.tools import TOOL_REGISTRY

for name in sorted(TOOL_REGISTRY.keys()):
    tool_class = TOOL_REGISTRY[name]
    description = getattr(tool_class, 'description', 'N/A')
    print(f"• {name}: {description}")
```

### How Tools are Found

```
@register_tool('my_tool')
        ↓
Added to TOOL_REGISTRY
        ↓
Agent requests 'my_tool'
        ↓
Registry returns tool class
        ↓
Agent instantiates and uses
```

## 💼 Best Practices

### 1. Write Excellent Descriptions

```python
# ❌ Bad
description = 'Does math'

# ✅ Good
description = 'Performs mathematical operations on two numbers including addition, subtraction, multiplication, and division'
```

### 2. Validate Inputs

```python
def call(self, params: str, **kwargs) -> str:
    args = json5.loads(params)

    # Validate
    if args['value'] < 0:
        return json.dumps({'error': 'Value must be positive'})

    # Process
    result = process(args['value'])
    return json.dumps({'result': result})
```

### 3. Return Structured Data

```python
# ✅ Good - structured JSON
return json.dumps({
    'result': 42,
    'status': 'success',
    'message': 'Calculation complete'
})

# ❌ Bad - plain text
return "The answer is 42"
```

### 4. Handle Errors Gracefully

```python
def call(self, params: str, **kwargs) -> str:
    try:
        args = json5.loads(params)
        result = risky_operation(args)
        return json.dumps({'result': result})
    except Exception as e:
        return json.dumps({
            'error': str(e),
            'type': type(e).__name__
        })
```

## 🔗 Related Resources

### Official Documentation
- [Tool Development Guide](/docs/tool.md)
- [Custom Tool Example](/examples/assistant_add_custom_tool.py)
- [Built-in Tools Source](/qwen_agent/tools/)

### Next Steps
- **Day 8**: Assistant Agent - Automatic tool orchestration
- **Day 9**: RAG Systems - Document-based tools
- **Day 10**: Multi-Agent - Tools calling tools

## 💡 Key Takeaways

1. **Tools are Python classes** - Inherit from BaseTool
2. **@register_tool is convenient** - But not required
3. **JSON Schema is powerful** - Use enums, arrays, nested objects
4. **Always use json5** - More forgiving than json
5. **Descriptions matter** - They teach the LLM when to use the tool
6. **Test tools directly** - Before agent integration
7. **Stateful tools are powerful** - But manage carefully
8. **Return structured data** - JSON is better than plain text

---

**🎉 Congratulations!**

You can now create custom tools that give your AI agents superpowers!

Your agents can now:
- ✅ Call external APIs
- ✅ Query databases
- ✅ Generate images
- ✅ Process data
- ✅ Perform calculations
- ✅ And anything else you can code!

