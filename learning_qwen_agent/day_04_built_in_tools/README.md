# Day 4: Built-in Tools - Giving Your Agent Superpowers

## 📚 Overview

Welcome to Day 4! Today you'll learn how to give your AI agents **real capabilities** through tools. Large Language Models alone can only generate text, but with tools, they can execute code, read documents, generate images, and much more!

## 🎯 Learning Objectives

By the end of this day, you will:

1. **Understand why tools are essential** for LLM applications
2. **Master the BaseTool interface** that all tools follow
3. **Use CodeInterpreter** to execute Python code dynamically
4. **Use DocParser** to extract text from documents (PDF, DOCX, etc.)
5. **Create custom tools** like image generators
6. **See automatic tool selection** by agents
7. **Learn about MCP** (Model Context Protocol) for external tools

## 🛠️ Tools Covered

### Built-in Tools

- **code_interpreter**: Execute Python code for calculations, data analysis, and visualizations
- **doc_parser**: Extract text from PDF, DOCX, PPTX, Excel, HTML, and text files
- **amap_weather**: Weather information (requires API key)
- **image_gen**: Image generation (requires configuration)
- And 12+ more tools in the registry!

### Custom Tools

- **my_image_gen**: Custom image generation using free API

### MCP Tools (Preview)

- File system access
- Time and date operations
- Web page fetching
- SQLite database operations
- And many more from the community!

## 📖 What You'll Build

Throughout this notebook, you'll build:

1. **A calculation agent** that uses CodeInterpreter for exact math
2. **A data analysis tool** that processes datasets with pandas
3. **A visualization generator** that creates charts with matplotlib
4. **A document parser** that extracts text from various file formats
5. **A multi-tool agent** that automatically chooses the right tool

## 🔑 Key Concepts

### The BaseTool Pattern

Every tool in Qwen-Agent follows this simple interface:

```python
class BaseTool:
    name: str                    # Unique identifier
    description: str             # What this tool does (tells LLM when to use it)
    parameters: List[dict]       # What inputs it needs (JSON Schema)

    def call(self, params: str, **kwargs) -> Union[str, dict, list]:
        """Execute the tool's functionality"""
        pass
```

Think of it as:
- `name` = The tool's ID badge
- `description` = The tool's job description
- `parameters` = The tool's instruction manual
- `call()` = Pressing the "RUN" button

### Tool Calling Flow

1. **User makes a request** → "Calculate 15 factorial"
2. **Agent analyzes request** → "This requires computation"
3. **Agent selects tool** → code_interpreter (based on description)
4. **Agent generates parameters** → `{"code": "import math; print(math.factorial(15))"}`
5. **Agent calls tool** → Executes the code
6. **Agent returns result** → "15! = 1,307,674,368,000"

## 📝 Prerequisites

Before starting this day, make sure you have:

- ✅ Completed Days 1-3 (Understanding of LLM config and Message schema)
- ✅ Fireworks API key configured
- ✅ Additional dependencies installed:

```bash
pip install "qwen-agent[code_interpreter]"
pip install lxml  # For document parsing
```

## 🚀 Getting Started

### Quick Start

```python
import os
import json

# 1. Configure your API
os.environ['FIREWORKS_API_KEY'] = 'your-api-key-here'

llm_cfg = {
    'model': 'accounts/fireworks/models/qwen3-235b-a22b-thinking-2507',
    'model_server': 'https://api.fireworks.ai/inference/v1',
    'api_key': os.environ['FIREWORKS_API_KEY'],
    'generate_cfg': {'max_tokens': 32768, 'temperature': 0.6}
}

# 2. Use a tool directly
from qwen_agent.tools import CodeInterpreter

code_tool = CodeInterpreter()
result = code_tool.call(json.dumps({'code': 'print(2 + 2)'}))
print(result)  # Output: "4"

# 3. Or use an agent with tools
from qwen_agent.agents import Assistant

bot = Assistant(llm=llm_cfg, function_list=['code_interpreter'])

messages = [{'role': 'user', 'content': 'Calculate 100 factorial'}]
for response in bot.run(messages=messages):
    print(response)
```

## 📚 Detailed Tool Guide

### CodeInterpreter

**What it does:**
- Executes Python code in a sandboxed Jupyter kernel
- Supports all standard Python libraries (pandas, numpy, matplotlib, etc.)
- Can read/write files in the working directory
- Returns both stdout and stderr

**Example Use Cases:**
- Complex calculations and data analysis
- Creating visualizations and charts
- File processing and transformations
- Running algorithms

**Key Notes:**
- ⚠️ Code runs in YOUR environment (not fully sandboxed)
- Working directory: `/workspace/tools/code_interpreter/`
- Variables persist across calls (same session)
- Errors are caught and returned as messages

### DocParser

**What it does:**
- Extracts text from documents: PDF, DOCX, PPTX, XLSX, HTML, TXT
- Preserves document structure (headings, paragraphs)
- Chunks large documents automatically
- Returns metadata (source, title, chunk IDs)

**Return Format:**
```python
{
    'url': '/path/to/file.pdf',
    'title': 'Document Title',
    'raw': [
        {
            'content': 'Extracted text...',
            'metadata': {'source': '/path/to/file.pdf', 'chunk_id': 0},
            'token': 256
        },
        # More chunks...
    ]
}
```

**Example Use Cases:**
- Building RAG (Retrieval Augmented Generation) systems
- Analyzing PDF reports
- Extracting data from Excel files
- Processing Word documents

## 🎨 Creating Custom Tools

### Example: Image Generation Tool

```python
import json
import urllib.parse
from qwen_agent.tools.base import BaseTool, register_tool

@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    description = 'AI painting service, input text description, return image URL'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': 'Detailed description in English',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json.dumps({
            'image_url': f'https://image.pollinations.ai/prompt/{prompt}'
        })
```

### Using Your Custom Tool

```python
# Option 1: Direct call
tool = MyImageGen()
result = tool.call(json.dumps({'prompt': 'a cute cat'}))
print(result)

# Option 2: With an agent
bot = Assistant(llm=llm_cfg, function_list=['my_image_gen'])
messages = [{'role': 'user', 'content': 'Draw a sunset over mountains'}]
for response in bot.run(messages=messages):
    print(response)
```

## 🌐 MCP (Model Context Protocol)

MCP allows you to integrate external tools from the community!

### Available MCP Servers

- `@modelcontextprotocol/server-filesystem` - File system operations
- `@modelcontextprotocol/server-time` - Date and time
- `mcp-server-fetch` - Web page fetching
- `mcp-server-sqlite` - Database operations
- Many more at: https://github.com/modelcontextprotocol/servers

### MCP Configuration Example

```python
mcp_tools = [{
    'mcpServers': {
        'time': {
            'command': 'npx',
            'args': ['-y', '@modelcontextprotocol/server-time']
        }
    }
}]

bot = Assistant(
    llm=llm_cfg,
    function_list=['code_interpreter'] + mcp_tools  # Mix built-in and MCP!
)
```

**Requirements:**
- Node.js (for `npx` commands) or Python (for `uvx` commands)
- MCP server packages installed

## 🎓 Practice Exercises

The notebook includes hands-on exercises:

1. **Prime Numbers Calculator** - Generate primes under 100 and sum them
2. **Data Visualization** - Create a bar chart from sales data
3. **Multi-Tool Agent** - Build an agent with multiple capabilities
4. **Tool Registry Explorer** - Discover all available tools

## 🔗 Related Resources

### Official Documentation
- [Tool Development Guide](/docs/tool.md)
- [Built-in Tools Source](/qwen_agent/tools/)
- [MCP Servers](https://github.com/modelcontextprotocol/servers)

### Example Code
- [Custom Tool Example](/examples/assistant_add_custom_tool.py)
- [Vision Tool Use](/examples/qwen2vl_assistant_tooluse.py)

### Next Steps
- **Day 5**: Creating Your First Custom Agent
- **Day 6**: Advanced Function Calling Patterns
- **Day 7**: Building Complex Custom Tools

## 💡 Key Takeaways

1. **Tools transform LLMs** from text generators into capable assistants
2. **All tools follow BaseTool pattern** (name, description, parameters, call)
3. **CodeInterpreter is incredibly powerful** - it can do almost anything Python can do
4. **Agents choose tools automatically** based on tool descriptions
5. **You can mix built-in, custom, and MCP tools** in a single agent
6. **DocParser returns structured data** with chunks, metadata, and tokens

## 🚨 Important Notes

### Security Considerations
- CodeInterpreter runs code in YOUR environment
- Only use with trusted code or implement sandboxing
- Be careful with file system access
- Review generated code before execution

### Best Practices
- Write clear tool descriptions (helps LLM choose correctly)
- Define precise parameters (JSON Schema)
- Handle errors gracefully in `call()` method
- Test tools independently before agent integration
- Document return format clearly

### Troubleshooting

**Problem:** "Dependencies for Code Interpreter support are not installed"
```bash
Solution: pip install "qwen-agent[code_interpreter]"
```

**Problem:** "BeautifulSoup lxml parser not found"
```bash
Solution: pip install lxml
```

**Problem:** Agent not calling tools
```bash
Solution: Make tool description more specific and relevant to task
```

## 📊 Tool Comparison

| Tool | Use Case | Input | Output | Speed |
|------|----------|-------|--------|-------|
| code_interpreter | Code execution | Python code | stdout/stderr | Medium |
| doc_parser | Document reading | File path | Text chunks | Fast |
| my_image_gen | Image generation | Text prompt | Image URL | Fast |
| amap_weather | Weather info | Location | Weather data | Medium |

## 🎉 What You've Accomplished

After completing this day, you can:

- ✅ Explain why tools are essential for LLM applications
- ✅ Use CodeInterpreter for calculations and data analysis
- ✅ Use DocParser to extract text from documents
- ✅ Create custom tools following the BaseTool pattern
- ✅ Build agents that automatically select and use tools
- ✅ Understand MCP for community tools

**Ready to move on?** Tomorrow you'll learn how to create your own custom agents from scratch!

---

**Happy Building! 🚀**
