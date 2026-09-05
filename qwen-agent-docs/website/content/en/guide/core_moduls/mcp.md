# MCP (Model Context Protocol)

MCP (Model Context Protocol) is a standardized protocol that enables large language models (LLMs) to interact with external tools and services in a structured way. In the Qwen-Agent framework, MCP is deeply integrated to empower intelligent agents with capabilities such as file system access, memory management, database queries, and more.

This document provides a comprehensive guide on how to configure and use MCP within Qwen-Agent.

---

## 1. Prerequisites

### 1.1 Install Qwen-Agent with MCP Support

Install the stable version from PyPI:

```bash
pip install -U "qwen-agent[mcp]" "mcp<2"
```

Or install the latest development version from source:

```bash
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -U -e ./"[mcp]" "mcp<2"
```

Use MCP SDK 1.x: Qwen-Agent currently imports `streamablehttp_client`, which is not available under that name in SDK 2.x.

In a minimal environment, also install the dependencies imported by Qwen-Agent's shared utilities and tools:

```bash
pip install numpy soundfile tqdm python-dateutil
```

### 1.2 Install Required System Dependencies

Local MCP servers typically rely on Node.js or Python-based toolchains. Install the dependencies required by your chosen local servers (the remote example in section 2.3 does not need these):

- **Node.js** (latest LTS version)
- **uv** (version ≥ 0.4.18) – for running Python-based MCP servers
- **Git**
- **SQLite** (if using the SQLite MCP server)

#### On macOS (via Homebrew):
```bash
brew install node uv git sqlite3
```

#### On Windows (via winget):
```powershell
winget install --id=OpenJS.NodeJS -e
winget install --id=astral-sh.uv -e
winget install git.git sqlite.sqlite
```

> 💡 **Note**: Verify installations with commands like `node --version`, `uv --version`, `git --version`, and `sqlite3 --version`.

---

## 2. Configuring MCP Services

MCP services are defined via a `mcpServers` configuration block. This can be passed directly in your Python code or loaded from a file.

### 2.1 MCP Configuration Format (JSON)

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"]
    },
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "test.db"]
    }
  }
}
```

> **Explanation**:
> - `memory`: Provides short-term memory storage.
> - `filesystem`: Grants read/write access to files within a specified directory (security boundary enforced).
> - `sqlite`: Enables SQL queries against a local SQLite database.

### 2.2 Enable MCP in Your Agent Code

Pass the MCP configuration when initializing your agent:

```python
from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI

# Define MCP config as a Python dict
mcp_config = {
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "./workspace"]
        },
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"]
        }
    }
}

# Configure your LLM (e.g., via DashScope)
llm_cfg = {
    'model': 'qwen3-max',
    'model_type': 'qwen_dashscope',
    # 'api_key': 'YOUR_API_KEY',  # Optional; falls back to DASHSCOPE_API_KEY env var
}

# Create an MCP-enabled agent
agent = Assistant(
    llm=llm_cfg,
    system_message="You are an intelligent assistant with file access and memory capabilities.",
    function_list=[mcp_config],      # Critical: include mcp_config to enable MCP tools
)

# Run GUI Demo
chatbot_config = {
        'prompt.suggestions': [
           'Please build an introductory Python program and store it on my computer',
           'Write a diary entry to `notes/diary.txt`.'
           'I prefer writing documents in Markdown.',
        ]
    }
WebUI(
     agent,
     chatbot_config=chatbot_config,
 ).run()
```

---

### 2.3 Remote Web Search with Parallel

Qwen-Agent also connects directly to remote MCP servers over Streamable HTTP. [Parallel Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp) provides public web search and page extraction without a Parallel account or API key. Free access is rate limited.

Use this configuration with your existing `llm_cfg` from section 2.2:

```python
from qwen_agent.agents import Assistant

parallel_config = {
    "mcpServers": {
        "parallel-search": {
            "type": "streamable-http",
            "url": "https://search.parallel.ai/mcp"
        }
    }
}

agent = Assistant(llm=llm_cfg, function_list=[parallel_config])
```

Set `type` to `streamable-http` explicitly: a URL without this field defaults to SSE. No local server process or authentication header is needed. Your LLM configuration and any credentials it requires are separate.

Initializing the agent connects to Parallel and discovers `parallel-search-web_search` and `parallel-search-web_fetch`. Once enabled, the agent may call these tools during a conversation. Search queries, requested URLs, and any supplied objectives, context, or metadata go to Parallel. See Parallel's [Customer Terms](https://parallel.ai/customer-terms) and [Privacy Policy](https://parallel.ai/privacy-policy).

For example, ask the agent to find the official Python documentation for `asyncio` and summarize the page. To keep other tools, include their existing entries alongside `parallel_config` in `function_list`. To disable Parallel, remove `parallel_config` and create a new agent. This example does not change the built-in search provider or the local server configurations above.

---

## 3. Example Use Cases

### Use Case 1: Reading/Writing Local Files
**User query**: “Save one  notes to `notes/meeting_2025.txt`.”
→ The agent automatically uses the `filesystem` MCP server to write the file.

### Use Case 2: Remembering User Preferences
**User says**: “I prefer writing documents in Markdown.”
→ Agent stores this preference using the `memory` MCP server and recalls it in future interactions.

### Use Case 3: Querying a Local Database
With `sqlite` MCP, the agent can execute queries like:
“List all orders with sales over 10,000.”

---

## 4. Important Notes & Best Practices

1. **Security**:
   - The `filesystem` MCP server only accesses the explicitly allowed directory (e.g., `./workspace`). Never expose sensitive system paths.
   - **The MCP services may not be sandboxed**. Use only in trusted, local development environments—**not in production**.

2. **Service Lifecycle**:
   - Qwen-Agent starts configured local MCP services or connects to remote services when the agent is initialized.
   - For local services, ensure that commands like `npx` and `uvx` are available in your system’s `PATH`.

3. **Debugging Tips**:
   - Check terminal logs to confirm MCP services start successfully.
   - Test with official examples, such as [`assistant_mcp_sqlite_bot.py`](https://github.com/QwenLM/Qwen-Agent/blob/main/examples/assistant_mcp_sqlite_bot.py).

4. **Performance**:
   - Each local MCP server runs as a separate subprocess; remote servers use network connections. Avoid defining unnecessary services to reduce overhead.

---

## 5. References & Resources

- [Official MCP Servers Repository](https://github.com/modelcontextprotocol/servers)
- [Qwen-Agent MCP Example: SQLite Bot](https://github.com/QwenLM/Qwen-Agent/blob/main/examples/assistant_mcp_sqlite_bot.py)
- [MCP Cookbooks (Added May 2025)](https://github.com/QwenLM/Qwen-Agent/tree/main/examples)

---

By properly configuring MCP in Qwen-Agent, you can significantly extend your agent’s ability to interact with the real world—enabling robust, context-aware applications powered by Qwen’s reasoning and tool-use capabilities.
