# Day 6: Function Calling - Teaching LLMs to Use Tools

## 📚 Overview

Function calling is the **mechanism that enables LLMs to use tools**. It's the bridge between language understanding and real-world actions.

**Why It Matters:**
- Without it: LLM can only talk about checking weather
- With it: LLM can actually call a weather API and get real data

## 🎯 Learning Objectives

By the end of this day, you will:

1. **Understand the function calling flow** - How LLMs request tool execution
2. **Master function schemas** - Defining functions in JSON Schema format
3. **Use direct LLM function calling** - Without agent abstractions
4. **Configure fncall_prompt_type** - 'qwen' vs 'nous' formats
5. **Control function_choice** - When functions should be called
6. **Implement parallel function calls** - Multiple tools simultaneously
7. **Handle errors gracefully** - Malformed calls and edge cases

## 🔑 Core Concepts

### The Function Calling Flow

```
User Query → LLM (with function definitions) → Function Call Request →
Execute Function → Add Result to Messages → Call LLM Again → Final Answer
```

**Key Insight:** The LLM doesn't execute functions - it generates **structured JSON requests** for YOU to execute!

### Function Schema Format

Functions are defined using **JSON Schema**:

```python
{
    'name': 'get_weather',              # Unique identifier
    'description': 'Get current weather', # Tells LLM when to use it
    'parameters': {                      # JSON Schema
        'type': 'object',
        'properties': {
            'location': {
                'type': 'string',
                'description': 'City name'
            },
            'unit': {
                'type': 'string',
                'enum': ['celsius', 'fahrenheit']
            }
        },
        'required': ['location']
    }
}
```

## 🚀 Quick Start Example

```python
from qwen_agent.llm import get_chat_model
import json

# 1. Define your function
def get_weather(location, unit='fahrenheit'):
    # Your implementation
    return json.dumps({'temp': 72, 'condition': 'Sunny'})

# 2. Define the schema
functions = [{
    'name': 'get_weather',
    'description': 'Get current weather',
    'parameters': {
        'type': 'object',
        'properties': {
            'location': {'type': 'string'},
            'unit': {'type': 'string', 'enum': ['celsius', 'fahrenheit']}
        },
        'required': ['location']
    }
}]

# 3. Call LLM with functions
llm = get_chat_model({'model': 'qwen-plus-latest', ...})
messages = [{'role': 'user', 'content': 'Weather in Tokyo?'}]

for responses in llm.chat(messages=messages, functions=functions):
    if responses[-1].get('function_call'):
        # Execute the function
        fn_name = responses[-1]['function_call']['name']
        fn_args = json.loads(responses[-1]['function_call']['arguments'])
        result = get_weather(**fn_args)

        # Add result to messages
        messages.extend(responses)
        messages.append({
            'role': 'function',
            'name': fn_name,
            'content': result
        })
```

## 📖 Key Topics

### 1. fncall_prompt_type

Different models expect different function calling formats:

| Type | Description | When to Use |
|------|-------------|-------------|
| **'qwen'** | Qwen native format | DashScope Qwen models |
| **'nous'** | NousResearch format | OpenAI-compatible APIs |

```python
llm = get_chat_model({
    'model': 'qwen-plus',
    'generate_cfg': {
        'fncall_prompt_type': 'qwen'  # or 'nous'
    }
})
```

### 2. function_choice Parameter

Control when the LLM uses functions:

| Value | Behavior | Use Case |
|-------|----------|----------|
| **'auto'** | LLM decides | Normal operation |
| **'none'** | Never call | Force direct answer |
| **function_name** | Force specific function | Required tool use |

```python
# Auto (default)
llm.chat(messages, functions, extra_generate_cfg={'function_choice': 'auto'})

# Force function
llm.chat(messages, functions, extra_generate_cfg={'function_choice': 'get_weather'})

# Disable functions
llm.chat(messages, functions, extra_generate_cfg={'function_choice': 'none'})
```

### 3. Parallel Function Calls

When users ask about multiple things, LLM can call multiple functions at once:

```python
# Enable parallel calls
llm.chat(
    messages=messages,
    functions=functions,
    extra_generate_cfg={'parallel_function_calls': True}
)

# User: "Weather in Tokyo, Paris, and New York?"
# LLM returns 3 function calls in one response!
```

**Important:** Execute ALL function calls and add ALL results before calling LLM again.

## 🛠️ Error Handling

### Common Errors

1. **Malformed JSON** - LLM generates invalid JSON arguments
2. **Unknown function** - LLM tries non-existent function
3. **Missing parameters** - Required arguments omitted
4. **Type errors** - Wrong parameter types

### Safe Execution Pattern

```python
def safe_execute_function(function_call_msg, available_functions):
    try:
        fn_name = function_call_msg['function_call']['name']

        if fn_name not in available_functions:
            return json.dumps({'error': f'Function {fn_name} not found'})

        try:
            fn_args = json.loads(function_call_msg['function_call']['arguments'])
        except json.JSONDecodeError as e:
            return json.dumps({'error': f'Invalid JSON: {str(e)}'})

        result = available_functions[fn_name](**fn_args)
        return result

    except TypeError as e:
        return json.dumps({'error': f'Parameter error: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})
```

## 💡 Best Practices

### 1. Write Clear Descriptions

```python
# ❌ Bad
'description': 'Gets weather'

# ✅ Good
'description': 'Get current weather conditions including temperature, humidity, and forecast for a specified city'
```

### 2. Use Enums for Limited Choices

```python
'unit': {
    'type': 'string',
    'enum': ['celsius', 'fahrenheit']  # Only these values
}
```

### 3. Mark Required Parameters

```python
'parameters': {
    'type': 'object',
    'properties': {...},
    'required': ['location']  # Must be provided
}
```

### 4. Implement the Complete Loop

```python
MAX_TURNS = 5
for turn in range(MAX_TURNS):
    # Call LLM
    responses = llm.chat(messages, functions)
    messages.extend(responses)

    # Check for function calls
    fn_calls = [r for r in responses if r.get('function_call')]

    if not fn_calls:
        break  # Got final answer

    # Execute all function calls
    for fn_call in fn_calls:
        result = execute_function(fn_call)
        messages.append({
            'role': 'function',
            'name': fn_call['function_call']['name'],
            'content': result
        })
```

## ⚠️ Important Notes

### For Fireworks API Users

**Note:** The Qwen3-235B-Thinking model shows its reasoning process, which may interfere with standard function calling. For function calling examples, consider using:

```python
llm_cfg = {
    'model': 'accounts/fireworks/models/qwen3-235b-a22b-instruct-2507',
    'model_server': 'https://api.fireworks.ai/inference/v1',
    'api_key': os.environ['FIREWORKS_API_KEY'],
}
```

### Message Format

Function results must be added with `role='function'`:

```python
messages.append({
    'role': 'function',     # Not 'assistant' or 'user'!
    'name': 'get_weather',  # Function name
    'content': result       # Must be string (use json.dumps for dicts)
})
```

## 📊 Complete Example: Weather Assistant

```python
def create_weather_assistant():
    # Define function
    def get_weather(location, unit='fahrenheit'):
        # Mock implementation
        return json.dumps({'temp': 72, 'condition': 'Sunny'})

    # Define schema
    functions = [{
        'name': 'get_weather',
        'description': 'Get current weather in a city',
        'parameters': {
            'type': 'object',
            'properties': {
                'location': {'type': 'string'},
                'unit': {'type': 'string', 'enum': ['celsius', 'fahrenheit']}
            },
            'required': ['location']
        }
    }]

    available_functions = {'get_weather': get_weather}

    # Chat loop
    def chat(user_query, max_turns=5):
        messages = [{'role': 'user', 'content': user_query}]
        llm = get_chat_model(llm_cfg)

        for turn in range(max_turns):
            responses = []
            for responses in llm.chat(messages=messages, functions=functions):
                pass

            messages.extend(responses)

            fn_calls = [r for r in responses if r.get('function_call')]
            if not fn_calls:
                return responses[-1].get('content')

            for fn_call in fn_calls:
                fn_name = fn_call['function_call']['name']
                fn_args = json.loads(fn_call['function_call']['arguments'])
                result = available_functions[fn_name](**fn_args)

                messages.append({
                    'role': 'function',
                    'name': fn_name,
                    'content': result
                })

        return "Max turns reached"

    return chat

# Usage
chat = create_weather_assistant()
answer = chat("What's the weather in Tokyo?")
print(answer)
```

## 🔗 Related Resources

### Official Documentation
- [Function Calling Example](/examples/function_calling.py)
- [Parallel Function Calling](/examples/function_calling_in_parallel.py)
- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)

### Next Steps
- **Day 7**: Custom Tools - Build reusable tool classes
- **Day 8**: Assistant Agent - Automatic tool management
- **Day 10**: Multi-Agent - Agents calling agents

## 💡 Key Takeaways

1. **LLMs generate function requests** - They don't execute them
2. **Schemas teach the LLM** - Good descriptions = better tool selection
3. **It's a loop** - LLM → Function → LLM (repeat as needed)
4. **Handle errors gracefully** - LLMs can generate malformed calls
5. **Parallel calls are powerful** - Enable for better UX
6. **Test with different models** - Behavior varies by model
7. **fncall_prompt_type matters** - Match it to your model/API

---

**🎉 Congratulations!**

You now understand how LLMs use tools through function calling - the foundation of AI agents!

