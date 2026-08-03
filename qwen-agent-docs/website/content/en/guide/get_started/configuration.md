# Configuration

This document explains all configuration parameters of Agent.

## LLM configuration
This part explains all configuration parameters used when setting up an LLM backend in Qwen-Agent via the `llm_cfg` dictionary.

---

### 🧩 Parameters

| Parameter | Type | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|----------|------|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `model` | `str` | ✅ Yes | The model name to use.<br> e.g., `'qwen3-max'`, `'qwen3-vl-plus'`, `'qwen3-omni-flash'`, `'qwen3-coder-plus'`                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `model_type` | `str` | ✅ Yes | Specifies the model provider, and binds with model capability.<br><br>Use Alibaba Cloud’s DashScope API:<br>• `'qwen_dashscope'`: LLM, support Text --> Text. <br>• `'qwenvl_dashscope'`: VLM, support Text/Image/Video --> Text. <br>• `'qwenaudio_dashscope'`: Omni models, support Text/Image/Video/Audio --> Text. <br><br>Use an OpenAI-compatible API: <br>• `'oai'`: LLM, support Text --> Text. <br>• `'qwenvl_oai'`: VLM, support Text/Image/Video --> Text. <br>• `'qwenaudio_oai'`: Omni models, support Text/Image/Video/Audio --> Text. |
| `model_server` | `str` | ❌ Conditionally | Required only for OpenAI-compatible API, e.g., <br>• `'http://localhost:8000/v1'`: local server, <br>• `'https://dashscope.aliyuncs.com/compatible-mode/v1'`: OpenAI-compatible API of DashScope.                                                                                                                                                                                                                                                                                                                                                    |
| `api_key` | `str` | ❌ No | API key for authentication.<br>• **DashScope**: Can be provided here or via the `DASHSCOPE_API_KEY` environment variable<br>• **OpenAI-compatible API**: Can be provided here or via the `OPENAI_API_KEY` environment variable.                                                                                                                                                                                                                                                                                                                      |
| `generate_cfg` | `dict` | ❌ No | Controls generation behavior and parsing logic (see below)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

---

### ⚙️ `generate_cfg` — Generation & Parsing Control

| Parameter          | Type  | Default  | Description                                                                                                                                                                                                                                                                                                                                          |
|--------------------|-------|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `max_input_tokens` | `int` | 90000    | The maximum context length of the agent, when the context exceeds this length, [context management](../../core_moduls/context/) will be automatically performed. This parameter should be lower than the maximum input length supported by the model to ensure the normal operation of the agent.                                                    |
| `use_raw_api`      | `bool` | `False`  | Whether to use the model server’s native tool-call parsing (e.g., vLLM’s built-in parser).<br> We recommend set `True` for models in the qwen3-coder, qwen3-max, and subsequent series. It will be changed to the default `True` in the future.                                                                                                      |
| enable thinking    | —      | —        | Enables "thinking mode" if supported by the model. Depends on the parameter protocol of the model service side. <br>• DashScope: `enable_thinking=True` <br>• OpenAI-compatible API of DashScope: `'extra_body': {'enable_thinking': True}` <br>• OpenAI-compatible API of vLLM: `'extra_body': {'chat_template_kwargs': {'enable_thinking': True}}` |
| *(Other params)*   | —     | —        | Parameters directly transmitted to the model service, such as `top_p`, `temperature`, `max_tokens`, etc                                                                                                                                                                                                                                              |

---

### 📌 Examples

#### ✅ **Using DashScope API**
```python
llm_cfg = {
    'model': 'qwen3-max-preview',
    'model_type': 'qwen_dashscope',
    # 'api_key': 'your-key',  # Optional if DASHSCOPE_API_KEY env var is set
    'generate_cfg': {
        'enable_thinking': 'True',
        'use_raw_api': 'True',
        'top_p': 0.8,
    }
}
```

#### ✅ **Using Local Model (vLLM / SGLang)**

```python
llm_cfg = {
    'model': 'Qwen3-8B',
    'model_server': 'http://localhost:8000/v1',
    'api_key': 'EMPTY',
    'generate_cfg': {
        'top_p': 0.85,
        'extra_body': {'chat_template_kwargs': {'enable_thinking': True}},
    }
}
```

#### ✅ **Using an OpenAI-compatible multi-model gateway**

The same `model_server` / `base_url` pattern works with any OpenAI-compatible multi-model gateway — for example [DaoXE](https://daoxe.com/?utm_source=github&utm_medium=organic&utm_campaign=qwen-agent&utm_content=configuration) at `https://api.daoxe.com/v1`:

```python
llm_cfg = {
    'model': 'gpt-4o-mini',  # or any model id exposed by the gateway
    'model_server': 'https://api.daoxe.com/v1',  # base_url / api_base
    'api_key': 'YOUR_GATEWAY_KEY',
}
```

---

#### 🔒 Notes

- Parallel tool calls are supported by default.

---

For working examples, see the [examples/](https://github.com/QwenLM/Qwen-Agent/tree/main/examples) directory in the Qwen-Agent repository.


## Tool configuration

When initializing an `Assistant` (or any agent that supports tool calling), you can specify available tools via the `function_list` parameter.
This parameter supports **three distinct formats**, and the system automatically detects and loads the corresponding tools accordingly.
Below is a detailed explanation of the supported formats and usage examples.

---

### 1. Supported Input Types

The `function_list` accepts a **list**, where each element can be one of the following three types:

#### ✅ Type 1: String (`str`) — Reference a Pre-registered Built-in Tool
- **Purpose**: Quickly enable a tool already registered in `TOOL_REGISTRY`.
- **Format**: The name of the tool as a string.
- **Requirement**: The tool must be pre-registered (e.g., via `@register_tool`).
- **Example**:
  ```python
  "code_interpreter"
  ```

#### ✅ Type 2: Dictionary (`dict`) — Configure a Registered Tool or MCP Servers
There are two subtypes of dictionary formats:

##### (a) Standard Tool Configuration Dictionary
- **Purpose**: Pass custom configuration to a registered tool.
- **Format**:
  ```python
  {
      "name": "tool_name",      # Required: Name of a pre-registered tool
      "other_config": ...       # Optional: Additional configuration parameters
  }
  ```
- **Requirement**: The `name` must correspond to a tool already in `TOOL_REGISTRY`.
- **Example**:
  ```python
  {
      "name": "weather",
      "api_key": "your_key"
  }
  ```

##### (b) MCP Server Configuration Dictionary (special key: `'mcpServers'`)
- **Purpose**: Dynamically load a set of tools via the **Model Context Protocol (MCP)**.
- **Format**:
  ```python
  {
      "mcpServers": {
          "server_alias_1": {
              "command": "executable",
              "args": ["arg1", "arg2", ...]
          },
          "server_alias_2": { ... }
      }
  }
  ```
- **Behavior**:
  - The system calls `MCPManager().initConfig(...)` to launch MCP services and auto-discover available tools.
  - Each key under `mcpServers` (e.g., `"time"`, `"fetch"`) represents a separate MCP tool server.
- **Example**:
  ```python
  {
      "mcpServers": {
          "time": {
              "command": "uvx",
              "args": ["mcp-server-time", "--local-timezone=Asia/Shanghai"]
          },
          "fetch": {
              "command": "uvx",
              "args": ["mcp-server-fetch"]
          }
      }
  }
  ```

#### ✅ Type 3: `BaseTool` Instance — Directly Provide a Tool Object
- **Purpose**: Pass a fully instantiated tool object (for advanced customization).
- **Format**: An instance of a class that inherits from `BaseTool`.
- **Example** (pseudo-code):
  ```python
  my_tool = CustomSearchTool(config={...})
  # Then include my_tool directly in function_list
  ```

---

### 2. Handling Duplicate Tool Names

- If multiple entries attempt to register a tool with the **same name**, the system:
   **Overwrites** any previous tool with the **latest occurrence** in the list.

> ⚠️ Note: Avoid tools with the same name!

---

### 3. Full Usage Example

```python
tools = [
    # Type 1: String reference to a built-in tool
    "code_interpreter",

    # Type 2a: Dictionary-based configuration for a registered tool
    {
        "name": "weather",
        "api_key": "your_openweather_key"
    },

    # Type 2b: MCP server configuration
    {
        "mcpServers": {
            "time": {
                "command": "uvx",
                "args": ["mcp-server-time", "--local-timezone=Asia/Shanghai"]
            },
            "file": {
                "command": "uvx",
                "args": ["mcp-server-filesystem"]
            }
        }
    },

    # Type 3: Direct BaseTool instance (optional)
    # MyCustomTool(config={...})
]

bot = Assistant(
    llm=llm_cfg,
    function_list=tools
)
```

---

### 4. Common Errors

| Error | Cause | Solution |
|------|------|--------|
| `ValueError: Tool xxx is not registered.` | Attempted to use a tool name not present in `TOOL_REGISTRY` | Ensure the tool is registered, or use MCP / `BaseTool` instead |
| MCP server fails to start | Incorrect `command`/`args`, or missing MCP server in environment | Verify the command works in your terminal; ensure tools like `mcp-server-time` are installed (e.g., via `uvx`) |

---

### 5. Summary

The `function_list` parameter is designed to **flexibly support multiple tool integration strategies**:
- **Simple**: Use strings for quick access to built-in tools.
- **Configurable**: Use dictionaries to customize registered tools.
- **Extensible**: Use `mcpServers` to plug into the MCP ecosystem.
- **Fully Custom**: Pass `BaseTool` instances for complete control.

By combining these approaches, you can build powerful, extensible tool-calling agents.

---
