<!---
Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

中文 ｜ [English](./README.md)

<p align="center">
    <img src="https://qianwen-res.oss-accelerate-overseas.aliyuncs.com/logo_qwen_agent.png" width="400"/>
<p>
<br>

<p align="center">
          💜 <a href="https://chat.qwen.ai/"><b>Qwen Chat</b></a>&nbsp&nbsp | &nbsp&nbsp🤗 <a href="https://huggingface.co/Qwen">Hugging Face</a>&nbsp&nbsp | &nbsp&nbsp🤖 <a href="https://modelscope.cn/organization/qwen">ModelScope</a>&nbsp&nbsp | &nbsp&nbsp 📑 <a href="https://qwenlm.github.io/">Blog</a> &nbsp&nbsp ｜ &nbsp&nbsp📖 <a href="https://qwenlm.github.io/Qwen-Agent/en/">Documentation</a>

<br>
📊 <a href="https://qwenlm.github.io/Qwen-Agent/en/benchmarks/deepplanning/">Benchmark</a>&nbsp&nbsp | &nbsp&nbsp💬 <a href="https://github.com/QwenLM/Qwen/blob/main/assets/wechat.png">WeChat (微信)</a>&nbsp&nbsp | &nbsp&nbsp🫨 <a href="https://discord.gg/CV4E9rpNSD">Discord</a>&nbsp&nbsp
</p>

Qwen-Agent是一个开发框架。开发者可基于本框架开发Agent应用，充分利用基于通义千问模型（Qwen）的指令遵循、工具使用、规划、记忆能力。本项目也提供了浏览器助手、代码解释器、自定义助手等示例应用。
现在，Qwen-Agent 作为 [Qwen Chat](https://chat.qwen.ai/) 的后端运行。

# 更新
* 🔥🔥🔥Feb 16, 2026: 开源Qwen3.5，调用实例参考 [Qwen3.5 Agent Demo](./examples/assistant_qwen3.5.py)。
* Jan 27, 2026: 开源Agent评测基准[DeepPlanning](https://qwenlm.github.io/Qwen-Agent/en/benchmarks/deepplanning/)，增加Qwen-Agent[文档](https://qwenlm.github.io/Qwen-Agent/en/guide/)。
* Sep 23, 2025: 新增 [Qwen3-VL Tool-call Demo](./examples/cookbook_think_with_images.ipynb)，支持使用抠图、图搜、文搜等工具。
* Jul 23, 2025: 新增 [Qwen3-Coder Tool-call Demo](./examples/assistant_qwen3_coder.py)；新增原生API工具调用接口支持，例如可使用vLLM自带的工具调用解析。
* May 1, 2025: 新增 [Qwen3 Tool-call Demo](./examples/assistant_qwen3.py)；新增 [MCP cookbooks](./examples/)。
* Mar 18, 2025: 支持`reasoning_content`字段；调整默认的[Function Call模版](./qwen_agent/llm/fncall_prompts/nous_fncall_prompt.py)（适用于Qwen2.5系列通用模型、QwQ-32B）。如果需要使用旧版模版：请参考[样例](./examples/function_calling.py)传递参数。
* Mar 7, 2025: 新增[QwQ-32B Tool-call Demo](./examples/assistant_qwq.py)，支持并行、多步、多轮工具调用。
* Dec 3, 2024: GUI 升级为基于 Gradio 5。注意：如果需要使用GUI，Python版本需要3.10及以上。
* Sep 18, 2024: 新增[Qwen2.5-Math Demo](./examples/tir_math.py)以展示Qwen2.5-Math基于工具的推理能力。注意：代码执行工具未进行沙箱保护，仅适用于本地测试，不可用于生产。

# 开始上手

## 安装

- 从 PyPI 安装稳定版本：
```bash
pip install -U "qwen-agent[rag,code_interpreter,gui,mcp]"
# 或者，使用 `pip install -U qwen-agent` 来安装最小依赖。
# 可使用双括号指定如下的可选依赖：
#   [gui] 用于提供基于 Gradio 的 GUI 支持；
#   [rag] 用于支持 RAG；
#   [code_interpreter] 用于提供代码解释器相关支持；
#   [mcp] 用于支持 MCP。
```

- 或者，你可以从源码安装最新的开发版本：
```bash
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -e ./"[gui,rag,code_interpreter,mcp]"
# 或者，使用 `pip install -e ./` 安装最小依赖。
```


## 准备：模型服务

Qwen-Agent支持接入阿里云[DashScope](https://help.aliyun.com/zh/dashscope/developer-reference/quick-start)服务提供的Qwen模型服务，也支持通过OpenAI API方式接入开源的Qwen模型服务。

- 如果希望接入DashScope提供的模型服务，只需配置相应的环境变量`DASHSCOPE_API_KEY`为您的DashScope API Key。

- 或者，如果您希望部署并使用您自己的模型服务，请按照Qwen2的README中提供的指导进行操作，以部署一个兼容OpenAI接口协议的API服务。
具体来说，请参阅[vLLM](https://github.com/QwenLM/Qwen2?tab=readme-ov-file#vllm)一节了解高并发的GPU部署方式，或者查看[Ollama](https://github.com/QwenLM/Qwen2?tab=readme-ov-file#ollama)一节了解本地CPU（+GPU）部署。

注意对于QwQ和Qwen3模型，建议启动服务时**不加**`--enable-auto-tool-choice`和`--tool-call-parser hermes`两个参数，因为Qwen-Agent会自行解析vLLM的工具输出。
对于Qwen3-Coder，则建议开启以上两个参数，使用vLLM自带的工具解析，并搭配`use_raw_api`参数[使用](#如何传递llm参数给agent)。

## 快速开发

框架提供了大模型（LLM，继承自`class BaseChatModel`，并提供了[Function Calling](./examples/function_calling.py)功能）和工具（Tool，继承自`class BaseTool`）等原子组件，也提供了智能体（Agent）等高级抽象组件（继承自`class Agent`）。

以下示例演示了如何增加自定义工具，并快速开发一个带有设定、知识库和工具使用能力的智能体：

```py
import pprint
import urllib.parse
import json5
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.output_beautify import typewriter_print


# 步骤 1（可选）：添加一个名为 `my_image_gen` 的自定义工具。
@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    # `description` 用于告诉智能体该工具的功能。
    description = 'AI 绘画（图像生成）服务，输入文本描述，返回基于文本信息绘制的图像 URL。'
    # `parameters` 告诉智能体该工具有哪些输入参数。
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': '期望的图像内容的详细描述',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        # `params` 是由 LLM 智能体生成的参数。
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json5.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)


# 步骤 2：配置您所使用的 LLM。
llm_cfg = {
    # 使用 DashScope 提供的模型服务：
    'model': 'qwen-max-latest',
    'model_type': 'qwen_dashscope',
    # 'api_key': 'YOUR_DASHSCOPE_API_KEY',
    # 如果这里没有设置 'api_key'，它将读取 `DASHSCOPE_API_KEY` 环境变量。

    # 使用与 OpenAI API 兼容的模型服务，例如 vLLM 或 Ollama：
    # 'model': 'Qwen2.5-7B-Instruct',
    # 'model_server': 'http://localhost:8000/v1',  # base_url，也称为 api_base
    # 'api_key': 'EMPTY',

    # （可选） LLM 的超参数：
    'generate_cfg': {
        'top_p': 0.8
    }
}

# 步骤 3：创建一个智能体。这里我们以 `Assistant` 智能体为例，它能够使用工具并读取文件。
system_instruction = '''在收到用户的请求后，你应该：
- 首先绘制一幅图像，得到图像的url，
- 然后运行代码`requests.get(image_url)`以下载该图像，
- 最后从给定的文档中选择一个图像操作进行图像处理。
用 `plt.show()` 展示图像。
你总是用中文回复用户。'''
tools = ['my_image_gen', 'code_interpreter']  # `code_interpreter` 是框架自带的工具，用于执行代码，请参考FAQ进行配置。
files = ['./examples/resource/doc.pdf']  # 给智能体一个 PDF 文件阅读。
bot = Assistant(llm=llm_cfg,
                system_message=system_instruction,
                function_list=tools,
                files=files)

# 步骤 4：作为聊天机器人运行智能体。
messages = []  # 这里储存聊天历史。
while True:
    # 例如，输入请求 "绘制一只狗并将其旋转 90 度"。
    query = input('\n用户请求: ')
    # 将用户请求添加到聊天历史。
    messages.append({'role': 'user', 'content': query})
    response = []
    response_plain_text = ''
    print('机器人回应:')
    for response in bot.run(messages=messages):
        # 流式输出。
        response_plain_text = typewriter_print(response, response_plain_text)
    # 将机器人的回应添加到聊天历史。
    messages.extend(response)
```

除了使用框架自带的智能体实现（如`class Assistant`），您也可以通过继承`class Agent`来自行开发您的智能体实现。

框架还提供了便捷的GUI接口，支持为Agent快速部署Gradio Demo。
例如上面的例子中，可以使用以下代码快速启动Gradio Demo：

```py
from qwen_agent.gui import WebUI
WebUI(bot).run()  # bot is the agent defined in the above code, we do not repeat the definition here for saving space.
```

现在您可以在Web UI中和Agent对话了。更多使用示例，请参阅[examples](./examples)目录。

# FAQ
## 如何使用代码解释器工具？
我们提供了一种基于本地 Docker 容器的代码解释器实现。您可以为智能体启用内置的 `code interpreter` 工具，使其能够根据具体场景自主编写代码，在隔离的沙箱环境中安全执行，并返回执行结果。
⚠️ **注意**：在使用该工具前，请确保已在本地操作系统上安装并启动 Docker 服务。首次构建容器镜像所需时间取决于您的网络状况。Docker 的安装与配置请参考 [官方文档](https://docs.docker.com/desktop/)。

## 如何使用MCP？
可以在开源的[MCP Server网站](https://github.com/modelcontextprotocol/servers)上选择需要的工具，并配置相关环境。

Qwen-Agent中MCP调用格式：
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
具体可参考[MCP使用例子](./examples/assistant_mcp_sqlite_bot.py)

运行该例子需要额外安装的依赖有：
```
# Node.js（访问 Node.js 官网下载并安装最新版本, https://nodejs.org/）
# uv 0.4.18 或更高版本 (使用 uv --version 检查)
# Git (git --version 检查)
# SQLite (sqlite3 --version 检查)

# 对于 macOS 用户，可以使用 Homebrew 安装这些组件：
brew install uv git sqlite3

# 对于 Windows 用户，可以使用 winget 安装这些组件：
winget install --id=astral-sh.uv -e
winget install git.git sqlite.sqlite
```

## 支持函数调用（也称为工具调用）吗？

支持，LLM类提供了[函数调用](https://github.com/QwenLM/Qwen-Agent/blob/main/examples/function_calling.py)的支持。此外，一些Agent类如FnCallAgent和ReActChat也是基于函数调用功能构建的。

目前的默认工具调用模版原生支持 **并行工具调用**（Parallel Function call）。

## 如何传递LLM参数给Agent？
```py
llm_cfg = {
    # 使用的模型名：
    'model': 'qwen3-32b',
    # 使用的模型服务：
    'model_type': 'qwen_dashscope',
    # 如果这里没有设置 'api_key'，它将默认读取 `DASHSCOPE_API_KEY` 环境变量：
    'api_key': 'YOUR_DASHSCOPE_API_KEY',

    # 使用与 OpenAI API 兼容的模型服务，例如 vLLM 或 Ollama：
    # 'model': 'qwen3-32b',
    # 'model_server': 'http://localhost:8000/v1',  # base_url，也称为 api_base
    # 'api_key': 'EMPTY',

    # （可选） LLM 的超参数：
    'generate_cfg': {
        # 这个参数将影响tool-call解析逻辑。默认为False：
          # 设置为True：当content为 `<think>this is the thought</think>this is the answer`
          # 设置为False: 当回复为 reasoning_content 和 content
        # 'thought_in_content': True,

        # tool-call template：默认为nous（qwen3 推荐）
        # 'fncall_prompt_type': 'nous'

        # 最大输入长度，超过该长度会对messages截断，请根据模型API调整
        # 'max_input_tokens': 58000

        # 将直接输入模型API的参数，例如top_p, enable_thinking等，根据API规范传入：
        # 'top_p': 0.8

        # Using the API's native tool call interface
        # 'use_raw_api': True,
    }
}
```

## 如何让AI基于超长文档进行问答？

我们已发布了一个[快速的RAG解决方案](https://github.com/QwenLM/Qwen-Agent/blob/main/examples/assistant_rag.py)，以及一个虽运行成本较高但[准确度较高的智能体](https://github.com/QwenLM/Qwen-Agent/blob/main/examples/parallel_doc_qa.py)，用于在超长文档中进行问答。它们在两个具有挑战性的基准测试中表现出色，超越了原生的长上下文模型，同时更加高效，并在涉及100万字词上下文的“大海捞针”式单针查询压力测试中表现完美。欲了解技术细节，请参阅[博客](https://qwenlm.github.io/blog/qwen-agent-2405/)。

<p align="center">
    <img src="https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/qwen-agent-2405-blog-long-context-results.png" width="400"/>
<p>

# 应用：BrowserQwen

BrowserQwen 是一款基于 Qwen-Agent 构建的浏览器助手。如需了解详情，请参阅其[文档](browser_qwen_cn.md)。

# 免责声明

基于 Docker 容器的代码解释器仅挂载指定的工作目录，并已实施基础的沙盒隔离，但在生产环境中仍需谨慎使用。
