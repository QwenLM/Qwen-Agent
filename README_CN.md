中文 ｜ [English](./README.md)

<p align="center">
    <img src="https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/logo-qwen-agent.png" width="400"/>
<p>
<br>

Qwen-Agent是一个可定制的、可扩展的Agent代码框架。单Agent具有角色扮演、LLM调用、工具使用、规划、记忆等能力。同时框架支持多Agent相互调用或协同工作构建复杂的Agent应用。 主要具有以下特点：

- 简单的Agent实现流程：只需指定角色描述、LLM名称、工具名列表，即可实现一个Agent应用，框架内部自动实现工具使用、规划、记忆等工作流的编排。
- 统一的接口和高扩展性：框架具有清晰的工具、LLM注册机制，方便用户扩展能力更加丰富的Agent应用。
- 高复用性：框架内置大量工具，例如代码运行、天气查询、文生图等，同时内置大量具有基础能力的Agent，例如**写文章**、**文档问答**、**关键词生成**等，方便用户直接使用。
- 低耦合性：开发者可以方便的使用内置的工具、LLM、记忆等组件，而不需要绑定更上层的Agent。
- 丰富的用例： 在Qwen-Agent的基础上，我们实现了类型丰富的用例，包括**谁是卧底小游戏**、**五子棋人机大战**、**天气预报助手**等。


# 快速使用

## 下载安装
```bash
# 安装依赖
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -e ./
```

## 部署模型服务
目前，Qwen-Agent支持使用开源的Qwen模型，或通过阿里云提供的[DashScope](https://help.aliyun.com/zh/dashscope/developer-reference/quick-start)服务来访问Qwen系列模型：

使用DashScope提供的模型，请配置环境变量：
```bash
# 您需要将YOUR_DASHSCOPE_API_KEY替换为您的真实API-KEY。
export DASHSCOPE_API_KEY=YOUR_DASHSCOPE_API_KEY
````
<details>
  <summary>自己部署一个模型服务，可以参考<a href="https://github.com/QwenLM/Qwen/blob/main/README_CN.md#api">[Qwen项目]</a>，部署一个兼容OpenAI API的模型服务：</summary>

```bash
# 安装依赖
git clone git@github.com:QwenLM/Qwen.git
cd Qwen
pip install -r requirements.txt
pip install fastapi uvicorn "openai<1.0.0" "pydantic>=2.3.0" sse_starlette

# 启动模型服务，通过 -c 参数指定模型版本
# - 指定 --server-name 0.0.0.0 将允许其他机器访问您的模型服务
# - 指定 --server-name 127.0.0.1 则只允许部署模型的机器自身访问该模型服务
python openai_api.py --server-name 0.0.0.0 --server-port 7905 -c Qwen/Qwen-14B-Chat
```
目前，我们支持指定-c参数以加载 [Qwen 的 Hugging Face主页](https://huggingface.co/Qwen) 上的模型，比如`Qwen/Qwen-1_8B-Chat`、`Qwen/Qwen-7B-Chat`、`Qwen/Qwen-14B-Chat`、`Qwen/Qwen-72B-Chat`，以及它们的`Int4`和`Int8`版本。
</details>


## 运行样例
```bash
# 进入examples目录，运行样例
cd examples
python undercover_play.py
```

至此，您已经可以使用Qwen-Agent库来运行Agent应用了!

# Agent 快速开发
如需开发个人的Agent，也十分简单，只需指定角色描述、LLM名称、工具名列表等配置文件，实例化一个Assistant Agent对象，即可开始和您的Agent对话。框架内部自动实现工具使用、规划、记忆等工作流的编排。
```bash
from qwen_agent.prompts import Assistant

# config
role = '你扮演一个天气预报助手，你需要查询相应地区的天气，同时调用给你的画图工具绘制一张城市的图。'
llm_config = {
    'model': 'qwen-max',
    'model_server': 'dashscope',
    'generate_cfg': {
        'top_p': 0.8
    }
}
function_list = ['image_gen', 'amap_weather']

# init agent
bot = Assistant(function_list=function_list,
                llm=llm_config,
                system_message=role)

messages = []
while True:
    # input query
    print('\n\n=====User input====:')
    query = input()
    messages.append({'role': 'user', 'content': query})

    # run agent
    response_stream = bot.run(messages=messages)

    # result processing
    print('\n=====Bot====:')
    response = []
    for response in response_stream:
        print(response)

    messages.extend(response)


```

# 复杂应用：BrowserQwen
我们也在Qwen-Agent的基础上开发了一个复杂的多Agent协同的应用，名为BrowserQwen的**Chrome浏览器扩展**，它具有以下主要功能：

- 与Qwen讨论当前网页或PDF文档的内容。
- 在获得您的授权后，BrowserQwen会记录您浏览过的网页和PDF/Word/PPT材料，以帮助您快速了解多个页面的内容，总结您浏览过的内容，并自动化繁琐的文字工作。
- 集成各种插件，包括可用于数学问题求解、数据分析与可视化、处理文件等的**代码解释器**（**Code Interpreter**）。


## 用例演示

如果您更喜欢观看视频，而不是效果截图，可以参见[视频演示](#视频演示)。

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

支持环境：MacOS，Linux，Windows。

## 第一步 - 部署本地数据库服务

在这一步，您需要在您的本地机器上（即您可以打开Chrome浏览器的那台机器），部署维护个人浏览历史、对话历史的数据库服务。

如果您打算使用DashScope提供的模型服务的话，请执行以下命令启动数据库服务：

```bash
# 启动数据库服务，通过 --llm 参数指定您希望通过DashScope使用的具体模型
# 参数 --llm 可以是如下之一，按资源消耗从小到大排序：
#   - qwen-7b-chat （与开源的Qwen-7B-Chat相同模型）
#   - qwen-14b-chat （与开源的Qwen-14B-Chat相同模型）
#   - qwen-turbo
#   - qwen-plus
# 您需要将YOUR_DASHSCOPE_API_KEY替换为您的真实API-KEY。
export DASHSCOPE_API_KEY=YOUR_DASHSCOPE_API_KEY
python run_server.py --model_server dashscope --llm qwen-7b-chat --workstation_port 7864
```

如果您没有在使用DashScope、而是部署了自己的模型服务的话，请执行以下命令：

```bash
# 启动数据库服务，通过 --model_server 参数指定您在 Step 1 里部署好的模型服务
# - 若部署模型的机器 IP 为 123.45.67.89，则可指定 --model_server http://123.45.67.89:7905/v1
# - 若是同一台机器，则可指定 --model_server http://127.0.0.1:7905/v1
python run_server.py --model_server http://{MODEL_SERVER_IP}:7905/v1 --workstation_port 7864
```

现在您可以访问 [http://127.0.0.1:7864/](http://127.0.0.1:7864/) 来使用工作台（Workstation）的创作模式（Editor模式）和对话模式（Chat模式）了。

关于工作台的使用技巧，请参见工作台页面的文字说明、或观看[视频演示](#视频演示)。

## 第二步 - 安装浏览器助手

安装BrowserQwen的Chrome插件（又称Chrome扩展程序）：

1. 打开Chrome浏览器，在浏览器的地址栏中输入 `chrome://extensions/` 并按下回车键；
2. 确保右上角的 `开发者模式` 处于打开状态，之后点击 `加载已解压的扩展程序` 上传本项目下的 `browser_qwen` 目录并启用；
3. 单击谷歌浏览器右上角```扩展程序```图标，将BrowserQwen固定在工具栏。

注意，安装Chrome插件后，需要刷新页面，插件才能生效。

当您想让Qwen阅读当前网页的内容时：

1. 请先点击屏幕上的 `Add to Qwen's Reading List` 按钮，以授权Qwen在后台分析本页面。
2. 再单击浏览器右上角扩展程序栏的Qwen图标，便可以和Qwen交流当前页面的内容了。

## 视频演示

可查看以下几个演示视频，了解BrowserQwen的基本操作：

- 根据浏览过的网页、PDFs进行长文创作 [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_write_article_based_on_webpages_and_pdfs.mp4)
- 提取浏览内容使用代码解释器画图 [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_chat_with_docs_and_code_interpreter.mp4)
- 上传文件、多轮对话利用代码解释器分析数据 [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_code_interpreter_multi_turn_chat.mp4)

# 评测基准

我们也开源了一个评测基准，用于评估一个模型写Python代码并使用Code Interpreter进行数学解题、数据分析、及其他通用任务时的表现。评测基准见 [benchmark](benchmark/README.md) 目录，当前的评测结果如下：

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
