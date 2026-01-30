# Qwen-Agent Schema Documentation


## Overview

The `qwen-agent` schema provides a structured, type-safe messaging system to support advanced capabilities such as multimodal conversations, function calling, and reasoning chains.
Built on Pydantic, it ensures data integrity during construction, validation, and serialization while enabling flexible representation of multimodal content (text, images, files, audio, and video).

### Design Goals
- **Type Safety**: Enforced validation via Pydantic models.
- **Multimodal Support**: Messages can include heterogeneous media types.
- **Compatibility**: Aligns with OpenAI-style message formats while extending support for arbitrary metadata via `extra`.
- **Developer Experience**: Offers dictionary-like access (`__getitem__`, `.get()`), automatic exclusion of `None` fields during serialization, and intuitive debugging representations.

---

## Core Constants

```python
# Role types
SYSTEM = 'system'
USER = 'user'
ASSISTANT = 'assistant'
FUNCTION = 'function'

# Content types (used in ContentItem)
TEXT = 'text'
IMAGE = 'image'
FILE = 'file'
AUDIO = 'audio'
VIDEO = 'video'

# Message field names
ROLE = 'role'
CONTENT = 'content'
REASONING_CONTENT = 'reasoning_content'
NAME = 'name'
```

---

## Base Class: `BaseModelCompatibleDict`

All schema classes inherit from `BaseModelCompatibleDict`, which extends `pydantic.BaseModel` with dictionary-like behavior.

### Features
- **Dictionary-style access**:
  ```python
  msg = Message(role='user', content='Hello')
  print(msg['role'])  # → 'user'
  ```
- **Safe retrieval**:
  ```python
  msg.get('non_existent_key', 'default')  # → 'default'
  ```
- **Clean serialization** (automatically omits `None` fields):
  ```python
  msg.model_dump()  # fields with value=None are excluded by default
  ```
- **Readable string representation**: `str(msg)` returns the result of `model_dump()`.

---

## Core Schema Classes

### 1. `FunctionCall`

Represents a function invocation proposed or executed by the model.

```python
class FunctionCall(BaseModelCompatibleDict):
    name: str
    arguments: str  # JSON-encoded string
```

**Example**:
```python
fc = FunctionCall(name='get_weather', arguments='{"city": "Beijing"}')
print(fc.name)        # → 'get_weather'
print(fc.arguments)   # → '{"city": "Beijing"}'
```

---

### 2. `ContentItem`

Represents a **single** piece of multimodal content. **Exactly one** of its fields (`text`, `image`, `file`, `audio`, `video`) must be provided.

```python
class ContentItem(BaseModelCompatibleDict):
    text: Optional[str] = None
    image: Optional[str] = None   # e.g., base64-encoded data or URL
    file: Optional[str] = None    # file path or URL
    audio: Optional[Union[str, dict]] = None
    video: Optional[Union[str, list]] = None
```

#### Properties
- `.type` → `'text' | 'image' | 'file' | 'audio' | 'video'`
- `.value` → the associated string value (e.g., base64, URL, file path)

#### Validation
- **Mutual Exclusivity**: Only one field may be non-`None`. Providing zero or more than one field raises a `ValueError`.

**Examples**:
```python
# Valid
txt = ContentItem(text='Hello')
img = ContentItem(image='https://example.jpg')
img = ContentItem(image='data:image/png;base64,...')

# Invalid (raises ValueError)
bad = ContentItem(text='Hi', image='...')  # ❌ "Exactly one ... must be provided"
```

---

### 3. `Message`

Represents a single message in a conversation, supporting multimodal content and function calls.

```python
class Message(BaseModelCompatibleDict):
    role: Literal['system', 'user', 'assistant', 'function']
    content: Union[str, List[ContentItem]]
    reasoning_content: Optional[Union[str, List[ContentItem]]] = None
    name: Optional[str] = None
    function_call: Optional[FunctionCall] = None
    extra: Optional[dict] = None
```

#### Field Descriptions

| Field | Type | Description |
|------|------|-------------|
| `role` | `str` | Must be one of: `'system'`, `'user'`, `'assistant'`, `'function'` |
| `content` | `str` or `List[ContentItem]` | **Primary message content** – plain text or a list of multimodal items |
| `reasoning_content` | Optional | Stores the model’s **reasoning trace** (e.g., chain-of-thought), same format as `content` |
| `name` | Optional `str` | When `role == 'function'`, identifies the called function |
| `function_call` | Optional `FunctionCall` | When `role == 'assistant'`, indicates a suggested function to invoke |
| `extra` | Optional `dict` | Arbitrary metadata (e.g., token counts, logs, custom annotations) |

#### Construction Notes
- If `content` is `None`, it is automatically set to an empty string `''`.
- The `role` field is validated to ensure it matches one of the allowed values.

**Examples**:

**Plain text message**:
```python
msg = Message(role='user', content='What is the weather in Tokyo?')
```

**Multimodal input (text + image)**:
```python
content = [
    ContentItem(text='Describe this image:'),
    ContentItem(image='https://example.com/cat.jpg')
]
msg = Message(role='user', content=content)
```

**Assistant initiating a function call**:
```python
msg = Message(
    role='assistant',
    content='',
    function_call=FunctionCall(name='get_weather', arguments='{"city": "Tokyo"}')
)
```

**Function response**:
```python
msg = Message(
    role='function',
    name='get_weather',
    content='{"temperature": 25, "unit": "Celsius"}'
)
```

**Response with reasoning trace**:
```python
msgs = [Message(
    role='assistant',
    content='',
    reasoning_content='Step 1: Identify the city. Step 2: Fetch weather data...'
), Message(
    role='assistant',
    content='It is 25 degrees Celsius',
)]
```

---


## Compatibility Notes

- The Qwen Agent receives and returns a list of messages, and the `reasoning_content`, `content`, and `function_call` in a response will be stored in separate messages.
- Qwen agent will convert the data into the corresponding format (such as OpenAI Chat Completions format) when calling the model service.
- When accessing the agent/llm message in JSON format, the received return value is also JSON. Similarly, if the input is pydantic models, the return value is also pydantic models.
---
