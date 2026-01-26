# Qwen-Agent Features

Qwen-Agent is a powerful and flexible framework for building intelligent LLM-powered applications. Key features include:

- **Unified Agent Interface**
  High-level `Agent` base class with ready-to-use implementations (e.g., `Assistant`, `FnCallAgent`) for rapid development.

- **Advanced Tool Calling**
  Native support for **parallel**, **multi-step**, and **multi-turn** function/tool calls with automatic parsing and execution.

- **RAG**
  Efficient document QA over 1M+ tokens using hybrid RAG and agent-based decomposition—outperforming native long-context models in benchmarks.

- **Built-in Tools**
  Includes versatile tools out of the box:
  - `code_interpreter`: Execute Python code
  - `web_search` and `web_extractor`: Perform web searches and extract page content
  - `image_search`: Perform image searches with image
  - `image_zoom_in_tool`: Zoom in on a specific region of an image by cropping it based on a bounding box

- **MCP (Model Context Protocol) Integration**
  Seamlessly connect to external tools and services (e.g., github, filesystem, SQLite) via the open MCP standard.

- **Custom Tool Support**
  Easily define and register your own tools using the `@register_tool` decorator and `BaseTool` interface.

- **Multi-Model Compatibility**
  Supports Qwen3, Qwen3-VL, Qwen3-Omni, Qwen3-Coder, QwQ, Qwen2.5 series, and other Qwen models via:
  - Alibaba Cloud **DashScope API**
  - Local **OpenAI-compatible servers** (vLLM, SGLang, etc.)

- **Built-in Tool Call Parser**
  Adapted to Qwen's tool call template, qwen-agent can still use the model's tool calling capability normally when the model service does not support tool call parser. It also supports the use of the tool call parser that comes with the model service.

- **Context Management**
  Automatically manage the long text of the agent to ensure that it does not exceed the maximum length of the model while ensuring the effectiveness of the agent.

- **Web GUI with Gradio**
  One-line launch of interactive web demos: `WebUI(agent).run()`. Built with Gradio 5.

- **Rich Agent Applications**
  Reference implementations for:
  - VL agent with the ability to search and zoom in on images
  - Vision-Language Tool Calling Demo
  - Math Reasoning Agents
  - BrowserQwen: Web-browsing assistant

- **Streaming & Interactive Output**
  Full support for streaming responses with real-time token-by-token display.

- **Extensible Architecture**
  Modular design: swap LLMs, tools, memory, and agent planning strategies independently for custom agentic AI.
