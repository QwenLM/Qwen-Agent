中文 ｜ [English](./README.md)

<p align="center">
    <img src="https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/logo-qwen-agent.png" width="400"/>
<p>
<br>

Qwen-Agent是一个开发框架。开发者可基于本框架开发Agent应用，充分利用基于通义千问模型（Qwen）的指令遵循、工具使用、规划、记忆能力。本项目也提供了浏览器助手、代码解释器、自定义助手等示例应用。

# 开始上手

## 安装

```bash
# 安装依赖
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -e ./
```

## 准备：模型服务

Qwen-Agent支持接入阿里云[DashScope](https://help.aliyun.com/zh/dashscope/developer-reference/quick-start)服务提供的Qwen模型服务，也支持通过OpenAI API方式接入开源的Qwen模型服务。

如果希望接入DashScope提供的模型服务，只需配置相应的环境变量：

```bash
# 您需要将YOUR_DASHSCOPE_API_KEY替换为您的真实API-KEY。
export DASHSCOPE_API_KEY=YOUR_DASHSCOPE_API_KEY
```

如果希望自行部署OpenAI API模型服务，可以参考<a href="https://github.com/QwenLM/Qwen/blob/main/README_CN.md#api">Qwen</a>
项目，部署一个兼容OpenAI API的模型服务：

```bash
# 安装依赖
git clone git@github.com:QwenLM/Qwen.git
cd Qwen
pip install -r requirements.txt
pip install fastapi uvicorn "openai<1.0.0" "pydantic>=2.3.0" sse_starlette

# 启动模型服务
# - 通过 -c 参数指定模型版本，支持 https://huggingface.co/Qwen 上列出的开源模型
# - 指定 --server-name 0.0.0.0 将允许其他机器访问您的模型服务
# - 指定 --server-name 127.0.0.1 则只允许部署模型的机器自身访问该模型服务
python openai_api.py --server-name 0.0.0.0 --server-port 7905 -c Qwen/Qwen-72B-Chat
```

## 快速开发

框架提供了LLM和prompts等基础原子组件、以及Agent等高级抽象组件。以下示例以Assistant这个组件为例，演示如何增加自定义工具、快速开发一个带有设定和工具使用能力的Agent：

```py
import json
import json5
import urllib.parse
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool

llm_cfg = {
    # 如果使用DashScope提供的模型服务：
    'model': 'qwen-max',
    'model_server': 'dashscope',
    # 如果使用自行部署的OpenAI API模型服务：
    # 'model': 'Qwen',
    # 'model_server': 'http://127.0.0.1:7905/v1',

    # （可选）模型的推理超参：
    'generate_cfg': {
        'top_p': 0.8
    }
}
system = '你扮演一个天气预报助手，你需要查询相应地区的天气，同时调用给你的画图工具绘制一张城市的图。'


# 增加一个名为my_image_gen的自定义工具：
@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    description = 'AI绘画（图像生成）服务，输入文本描述和图像分辨率，返回根据文本信息绘制的图片URL。'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': '详细描述了希望生成的图像具有什么内容，例如人物、环境、动作等细节描述，使用英文',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)


tools = ['my_image_gen', 'amap_weather']  # amap_weather是框架预置的工具
bot = Assistant(llm=llm_cfg, system_message=system, function_list=tools)

messages = []
while True:
    query = input('user question: ')
    messages.append({'role': 'user', 'content': query})
    response = []
    for response in bot.run(messages=messages):
        print('bot response:', response)
    messages.extend(response)
```

框架中还提供了更多的原子组件供开发者组合。更多的迷你开发案例见[examples](./examples)目录。

# 示例应用：BrowserQwen

我们在Qwen-Agent的基础上开发了一个较为复杂的Agent应用，名为BrowserQwen的**Chrome浏览器扩展**，它具有以下主要功能：

- 与Qwen讨论当前网页或PDF文档的内容。
- BrowserQwen会记录您浏览过的网页和PDF/Word/PPT材料，帮助您了解多个页面的内容、总结浏览过的内容、自动化繁琐的文字工作。
- 集成各种插件，包括可用于数学问题求解、数据分析与可视化、处理文件等的**代码解释器**（**Code Interpreter**）。

## BrowserQwen 功能演示

可查看以下几个演示视频，了解BrowserQwen的核心功能和基本操作：

- 根据浏览过的网页、PDFs进行长文创作 [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_write_article_based_on_webpages_and_pdfs.mp4)
- 提取浏览内容使用代码解释器画图 [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_chat_with_docs_and_code_interpreter.mp4)
- 上传文件、多轮对话利用代码解释器分析数据 [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_code_interpreter_multi_turn_chat.mp4)

### 工作台 - 创作模式

**根据浏览过的网页、PDFs素材进行长文创作**

<figure>
    <img src="assets/screenshot-writing.png">
</figure>

**调用插件辅助富文本创作**

<figure>
    <img src="assets/screenshot-editor-movie.png">
</figure>

### 工作台 - 对话模式

**多网页问答**

<figure >
    <img src="assets/screenshot-multi-web-qa.png">
</figure>

**使用代码解释器绘制数据图表**

<figure>
    <img src="assets/screenshot-ci.png">
</figure>

### 浏览器助手

**网页问答**

<figure>
    <img src="assets/screenshot-web-qa.png">
</figure>

**PDF文档问答**

<figure>
    <img src="assets/screenshot-pdf-qa.png">
</figure>

## BrowserQwen 使用说明

### 第一步 - 部署本地数据库服务

在这一步，您需要在您的本地机器上（即您可以打开Chrome浏览器的那台机器），部署维护个人浏览历史、对话历史的数据库服务。

如果您使用DashScope提供的模型服务的话，请执行以下命令启动数据库服务：

```bash
# 启动数据库服务，通过 --llm 参数指定您希望通过DashScope使用的具体模型
# 参数 --llm 可以是如下之一，按资源消耗从小到大排序：
#   - qwen-7b/14b/72b-chat （与开源的Qwen-7B/14B/72B-Chat相同模型）
#   - qwen-turbo, qwen-plus, qwen-max
# 您需要将YOUR_DASHSCOPE_API_KEY替换为您的真实API-KEY。
python run_server.py --api_key YOUR_DASHSCOPE_API_KEY --model_server dashscope --llm qwen-max --workstation_port 7864
```

如果您没有在使用DashScope、而是部署了自己的模型服务的话，请执行以下命令：

```bash
# 启动数据库服务，通过 --model_server 参数指定部署好的模型服务
# - 若部署模型的机器 IP 为 123.45.67.89，则可指定 --model_server http://123.45.67.89:7905/v1
# - 若模型服务和数据库服务是同一台机器，则可指定 --model_server http://127.0.0.1:7905/v1
python run_server.py --model_server http://{MODEL_SERVER_IP}:7905/v1 --workstation_port 7864
```

现在您可以访问 [http://127.0.0.1:7864/](http://127.0.0.1:7864/) 来使用工作台（Workstation）的创作模式（Editor模式）和对话模式（Chat模式）了。

### 第二步 - 安装浏览器助手

安装BrowserQwen的Chrome插件（又称Chrome扩展程序）：

1. 打开Chrome浏览器，在浏览器的地址栏中输入 `chrome://extensions/` 并按下回车键；
2. 确保右上角的 `开发者模式` 处于打开状态，之后点击 `加载已解压的扩展程序` 上传本项目下的 `browser_qwen` 目录并启用；
3. 单击谷歌浏览器右上角```扩展程序```图标，将BrowserQwen固定在工具栏。

注意，安装Chrome插件后，需要刷新页面，插件才能生效。

当您想让Qwen阅读当前网页的内容时：

1. 请先点击屏幕上的 `Add to Qwen's Reading List` 按钮，以授权Qwen在后台分析本页面。
2. 再单击浏览器右上角扩展程序栏的Qwen图标，便可以和Qwen交流当前页面的内容了。

# 评测基准

我们也开源了一个评测基准，用于评估一个模型写Python代码并使用Code
Interpreter进行数学解题、数据分析、及其他通用任务时的表现。评测基准见 [benchmark](benchmark/README.md) 目录，当前的评测结果如下：

<table>
    <tr>
        <th colspan="5" align="center">In-house Code Interpreter Benchmark (Version 20231206)</th>
    </tr>
    <tr>
        <th rowspan="2" align="center">Model</th>
        <th colspan="3" align="center">代码执行结果正确性 (%)</th>
        <th colspan="1" align="center">生成代码的可执行率 (%)</th>
    </tr>
    <tr>
        <th align="center">Math↑</th><th align="center">Visualization-Hard↑</th><th align="center">Visualization-Easy↑</th><th align="center">General↑</th>
    </tr>
    <tr>
        <td>GPT-4</td>
        <td align="center">82.8</td>
        <td align="center">66.7</td>
        <td align="center">60.8</td>
        <td align="center">82.8</td>
    </tr>
    <tr>
        <td>GPT-3.5</td>
        <td align="center">47.3</td>
        <td align="center">33.3</td>
        <td align="center">55.7</td>
        <td align="center">74.1</td>
    </tr>
    <tr>
        <td>LLaMA2-13B-Chat</td>
        <td align="center">8.3</td>
        <td align="center">1.2</td>
        <td align="center">15.2</td>
        <td align="center">48.3</td>
    </tr>
    <tr>
        <td>CodeLLaMA-13B-Instruct</td>
        <td align="center">28.2</td>
        <td align="center">15.5</td>
        <td align="center">21.5</td>
        <td align="center">74.1</td>
    </tr>
    <tr>
        <td>InternLM-20B-Chat</td>
        <td align="center">34.6</td>
        <td align="center">10.7</td>
        <td align="center">24.1</td>
        <td align="center">65.5</td>
    </tr>
    <tr>
        <td>ChatGLM3-6B</td>
        <td align="center">54.2</td>
        <td align="center">4.8</td>
        <td align="center">15.2</td>
        <td align="center">62.1</td>
    </tr>
    <tr>
        <td>Qwen-1.8B-Chat</td>
        <td align="center">25.6</td>
        <td align="center">21.4</td>
        <td align="center">22.8</td>
        <td align="center">65.5</td>
    </tr>
    <tr>
        <td>Qwen-7B-Chat</td>
        <td align="center">41.9</td>
        <td align="center">23.8</td>
        <td align="center">38.0</td>
        <td align="center">67.2</td>
    </tr>
    <tr>
        <td>Qwen-14B-Chat</td>
        <td align="center">58.4</td>
        <td align="center">31.0</td>
        <td align="center">45.6</td>
        <td align="center">65.5</td>
    </tr>
    <tr>
        <td>Qwen-72B-Chat</td>
        <td align="center">72.7</td>
        <td align="center">41.7</td>
        <td align="center">43.0</td>
        <td align="center">82.8</td>
    </tr>
</table>

# 免责声明

本项目并非正式产品，而是一个概念验证项目，用于演示Qwen系列模型的能力。

> 重要提示：代码解释器未进行沙盒隔离，会在部署环境中执行代码。请避免向Qwen发出危险指令，切勿将该代码解释器直接用于生产目的。
