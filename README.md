[中文](https://github.com/QwenLM/Qwen-Agent/blob/main/README_CN.md) ｜ English

<p align="center">
    <img src="https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/logo-qwen-agent.png" width="400"/>
<p>
<br>

<p align="center">
          💜 <a href="https://chat.qwen.ai/"><b>Qwen Chat</b></a>&nbsp&nbsp | &nbsp&nbsp🤗 <a href="https://huggingface.co/Qwen">Hugging Face</a>&nbsp&nbsp | &nbsp&nbsp🤖 <a href="https://modelscope.cn/organization/qwen">ModelScope</a>&nbsp&nbsp | &nbsp&nbsp 📑 <a href="https://qwenlm.github.io/">Blog</a> &nbsp&nbsp ｜ &nbsp&nbsp📖 <a href="https://qwen.readthedocs.io/">Documentation</a>

<br>
💬 <a href="https://github.com/QwenLM/Qwen/blob/main/assets/wechat.png">WeChat (微信)</a>&nbsp&nbsp | &nbsp&nbsp🫨 <a href="https://discord.gg/CV4E9rpNSD">Discord</a>&nbsp&nbsp
</p>


Qwen-Agent is a framework for developing LLM applications based on the instruction following, tool usage, planning, and
memory capabilities of Qwen.
It also comes with example applications such as Browser Assistant, Code Interpreter, and Custom Assistant.
Now Qwen-Agent plays as the backend of [Qwen Chat](https://chat.qwen.ai/).

# News
* 🔥🔥🔥May 1, 2025: Add [Qwen3 Tool-call Demo](./examples/assistant_qwen3.py).
* Mar 18, 2025: Support for the `reasoning_content` field; adjust the default [Function Call template](./qwen_agent/llm/fncall_prompts/nous_fncall_prompt.py), which is applicable to the Qwen2.5 series general models and QwQ-32B. If you need to use the old version of the template, please refer to the [example](./examples/function_calling.py) for passing parameters.
* Mar 7, 2025: Added [QwQ-32B Tool-call Demo](./examples/assistant_qwq.py). It supports parallel, multi-step, and multi-turn tool calls.
* Dec 3, 2024: Upgrade GUI to Gradio 5 based. Note: GUI requires Python 3.10 or higher.
* Sep 18, 2024: Added [Qwen2.5-Math Demo](./examples/tir_math.py) to showcase the Tool-Integrated Reasoning capabilities of Qwen2.5-Math. Note: The python executor is not sandboxed and is intended for local testing only, not for production use.

# Getting Started

## Installation

- Install the stable version from PyPI:
```bash
pip install -U "qwen-agent[gui,rag,code_interpreter,mcp]"
# Or use `pip install -U qwen-agent` for the minimal requirements.
# The optional requirements, specified in double brackets, are:
#   [gui] for Gradio-based GUI support;
#   [rag] for RAG support;
#   [code_interpreter] for Code Interpreter support;
#   [mcp] for MCP support.
```

- Alternatively, you can install the latest development version from the source:
```bash
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -e ./"[gui,rag,code_interpreter,mcp]"
# Or `pip install -e ./` for minimal requirements.
```

## Preparation: Model Service

You can either use the model service provided by Alibaba
Cloud's [DashScope](https://help.aliyun.com/zh/dashscope/developer-reference/quick-start), or deploy and use your own
model service using the open-source Qwen models.

- If you choose to use the model service offered by DashScope, please ensure that you set the environment
variable `DASHSCOPE_API_KEY` to your unique DashScope API key.

- Alternatively, if you prefer to deploy and use your own model service, please follow the instructions provided in the README of Qwen2 for deploying an OpenAI-compatible API service.
Specifically, consult the [vLLM](https://github.com/QwenLM/Qwen2?tab=readme-ov-file#vllm) section for high-throughput GPU deployment or the [Ollama](https://github.com/QwenLM/Qwen2?tab=readme-ov-file#ollama) section for local CPU (+GPU) deployment.
For the QwQ and Qwen3 model, it is recommended to add the `--enable-reasoning` and `--reasoning-parser deepseek_r1` parameters when starting the service. **Do not** add the `--enable-auto-tool-choice` and `--tool-call-parser hermes` parameters, as Qwen-Agent will parse the tool outputs from vLLM on its own.

## Developing Your Own Agent

Qwen-Agent offers atomic components, such as LLMs (which inherit from `class BaseChatModel` and come with [function calling](https://github.com/QwenLM/Qwen-Agent/blob/main/examples/function_calling.py)) and Tools (which inherit
from `class BaseTool`), along with high-level components like Agents (derived from `class Agent`).

The following example illustrates the process of creating an agent capable of reading PDF files and utilizing tools, as
well as incorporating a custom tool:

```py
import pprint
import urllib.parse
import json5
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.output_beautify import typewriter_print


# Step 1 (Optional): Add a custom tool named `my_image_gen`.
@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    # The `description` tells the agent the functionality of this tool.
    description = 'AI painting (image generation) service, input text description, and return the image URL drawn based on text information.'
    # The `parameters` tell the agent what input parameters the tool has.
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': 'Detailed description of the desired image content, in English',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        # `params` are the arguments generated by the LLM agent.
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json5.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)


# Step 2: Configure the LLM you are using.
llm_cfg = {
    # Use the model service provided by DashScope:
    'model': 'qwen-max-latest',
    'model_server': 'dashscope',
    # 'api_key': 'YOUR_DASHSCOPE_API_KEY',
    # It will use the `DASHSCOPE_API_KEY' environment variable if 'api_key' is not set here.

    # Use a model service compatible with the OpenAI API, such as vLLM or Ollama:
    # 'model': 'Qwen2.5-7B-Instruct',
    # 'model_server': 'http://localhost:8000/v1',  # base_url, also known as api_base
    # 'api_key': 'EMPTY',

    # (Optional) LLM hyperparameters for generation:
    'generate_cfg': {
        'top_p': 0.8
    }
}

# Step 3: Create an agent. Here we use the `Assistant` agent as an example, which is capable of using tools and reading files.
system_instruction = '''After receiving the user's request, you should:
- first draw an image and obtain the image url,
- then run code `request.get(image_url)` to download the image,
- and finally select an image operation from the given document to process the image.
Please show the image using `plt.show()`.'''
tools = ['my_image_gen', 'code_interpreter']  # `code_interpreter` is a built-in tool for executing code.
files = ['./examples/resource/doc.pdf']  # Give the bot a PDF file to read.
bot = Assistant(llm=llm_cfg,
                system_message=system_instruction,
                function_list=tools,
                files=files)

# Step 4: Run the agent as a chatbot.
messages = []  # This stores the chat history.
while True:
    # For example, enter the query "draw a dog and rotate it 90 degrees".
    query = input('\nuser query: ')
    # Append the user query to the chat history.
    messages.append({'role': 'user', 'content': query})
    response = []
    response_plain_text = ''
    print('bot response:')
    for response in bot.run(messages=messages):
        # Streaming output.
        response_plain_text = typewriter_print(response, response_plain_text)
    # Append the bot responses to the chat history.
    messages.extend(response)
```

In addition to using built-in agent implementations such as `class Assistant`, you can also develop your own agent implemetation by inheriting from `class Agent`.

The framework also provides a convenient GUI interface, supporting the rapid deployment of Gradio Demos for Agents.
For example, in the case above, you can quickly launch a Gradio Demo using the following code:

```py
from qwen_agent.gui import WebUI
WebUI(bot).run()  # bot is the agent defined in the above code, we do not repeat the definition here for saving space.
```
Now you can chat with the Agent in the web UI. Please refer to the [examples](https://github.com/QwenLM/Qwen-Agent/blob/main/examples) directory for more usage examples.

# FAQ

## How to Use MCP?

You can select the required tools on the open-source [MCP server website](https://github.com/modelcontextprotocol/servers) and configure the relevant environment.

Example of MCP invocation format:
```
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
        "sqlite" : {
            "command": "uvx",
            "args": [
                "mcp-server-sqlite",
                "--db-path",
                "test.db"
            ]
        }
    }
}
```
For more details, you can refer to the [MCP usage example](./examples/assistant_mcp_sqlite_bot.py)

The dependencies required to run this example are as follows:
```
# Node.js (Download and install the latest version from the Node.js official website)
# uv 0.4.18 or higher (Check with uv --version)
# Git (Check with git --version)
# SQLite (Check with sqlite3 --version)

# For macOS users, you can install these components using Homebrew:
brew install uv git sqlite3

# For Windows users, you can install these components using winget:
winget install --id=astral-sh.uv -e
winget install git.git sqlite.sqlite
```
## Do you have function calling (aka tool calling)?

Yes. The LLM classes provide [function calling](https://github.com/QwenLM/Qwen-Agent/blob/main/examples/function_calling.py). Additionally, some Agent classes also are built upon the function calling capability, e.g., FnCallAgent and ReActChat.

## How to do question-answering over super-long documents involving 1M tokens?

We have released [a fast RAG solution](https://github.com/QwenLM/Qwen-Agent/blob/main/examples/assistant_rag.py), as well as [an expensive but competitive agent](https://github.com/QwenLM/Qwen-Agent/blob/main/examples/parallel_doc_qa.py), for doing question-answering over super-long documents. They have managed to outperform native long-context models on two challenging benchmarks while being more efficient, and perform perfectly in the single-needle "needle-in-the-haystack" pressure test involving 1M-token contexts. See the [blog](https://qwenlm.github.io/blog/qwen-agent-2405/) for technical details.

<p align="center">
    <img src="https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/qwen-agent-2405-blog-long-context-results.png" width="400"/>
<p>

# Application: BrowserQwen

BrowserQwen is a browser assistant built upon Qwen-Agent. Please refer to its [documentation](https://github.com/QwenLM/Qwen-Agent/blob/main/browser_qwen.md) for details.

# Disclaimer

The code interpreter is not sandboxed, and it executes code in your own environment. Please do not ask Qwen to perform dangerous tasks, and do not directly use the code interpreter for production purposes.
