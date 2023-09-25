# Qwen-Agent

中文 ｜ [English](./README.md)

Qwen-Agent是一个基于开源模型通义千问（Qwen）的代码库，它将工具使用、规划生成、记忆等组件集合在一起。目前，我们已经开发了一个名为BrowserQwen的浏览器扩展程序，它能够方便地辅助您进行网页和PDF文档的理解、知识整合和富文本内容编辑工作。以下是BrowserQwen的特点：

- 将Qwen集成到浏览器扩展程序中，支持在浏览器中与Qwen进行讨论，聊一聊当前Web页面、PDF文档的内容。

- 在您允许的前提下，BrowserQwen将记录您浏览过的网页和PDF素材，以帮助您根据浏览内容完成编辑工作。通过BrowserQwen，您可以快速完成多网页内容的理解、浏览内容的整理和新文章的撰写等繁琐工作。

- 支持插件调用，目前已经集成了代码解释器（Code Interpreter）等插件，代码解释器能够支持上传文件进行数据分析等功能。

目前，我们支持两种模型：Qwen-14B-Chat（推荐）和Qwen-7B-Chat。对于Qwen-7B-Chat模型，请使用2023年9月25日之后从官方Github和HuggingFace重新拉取的版本，因为代码和模型权重都发生了变化。

# 用例演示

## 工作台 - 创作模式

**根据浏览过的网页、PDFs素材进行长文创作**

<figure>
    <img src="assets/screenshot-writing.png">
</figure>

**调用插件辅助富文本创作**

<figure>
    <img src="assets/screenshot-editor-movie.png">
</figure>

## 工作台 - 对话模式

**多网页问答**

<figure >
    <img src="assets/screenshot-multi-web-qa.png">
</figure>

**使用代码解释器绘制数据图表**

<figure>
    <img src="assets/screenshot-ci.png">
</figure>

## 浏览器助手

**网页问答**

<figure>
    <img src="assets/screenshot-web-qa.png">
</figure>

**PDF文档问答**

<figure>
    <img src="assets/screenshot-pdf-qa.png">
</figure>

# BrowserQwen 使用说明

支持环境：MacOS，Linux。尚未实现对Windows的支持。

## Step 1. 部署模型服务

参考[Qwen项目](https://github.com/QwenLM/Qwen/blob/main/README_CN.md#api)，部署一个兼容OpenAI API的模型服务：

```
# 安装依赖
git clone git@github.com:QwenLM/Qwen.git
cd Qwen
pip install -r requirements.txt
pip install fastapi uvicorn openai pydantic>=2.3.0 sse_starlette

# 启动模型服务，通过 -c 参数指定模型版本
python openai_api.py --server-name 127.0.0.1 --server-port 7905 -c QWen/QWen-14B-Chat
```

我们推荐使用QWen-14B-Chat模型。如果您想使用Qwen-7B-Chat模型，请确保使用的是2023年9月25日之后从官方HuggingFace重新拉取的版本，因为代码和模型权重都发生了变化。

## Step 2. 部署本地数据库服务

在您的本地机器上（即您可以打开Chrome浏览器的那台机器），部署维护个人浏览历史、对话历史的数据库服务：

```
# 安装依赖
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -r requirements.txt

# 启动数据库服务，通过 --model_server 参数指定您在 Step 1 里部署好的模型服务
python run_server.py --model_server http://127.0.0.1:7905/v1 --workstation_port 7864
```

现在您可以访问 [http://127.0.0.1:7864/](http://127.0.0.1:7864/) 来使用Workstation的Editor模式和Chat模式了。

关于Workstation的使用技巧，请参见Workstation页面的文字说明。

## Step 3. 安装浏览器助手

安装BrowserQwen的Chrome插件（又称Chrome扩展程序）：

1. 打开Chrome浏览器，在浏览器的地址栏中输入 `chrome://extensions/` 并按下回车键；
2. 点击 `加载已解压的扩展程序`，上传本项目下的 `browser_qwen` 目录并启用；
3. 单击谷歌浏览器右上角```扩展程序```图标，将BrowserQwen固定在工具栏。

注意，安装Chrome插件后，需要刷新页面，插件才能生效。

当您想让Qwen阅读当前网页的内容时：

1. 请先点击屏幕上的 `Add to Qwen's Reading List` 按钮，以授权Qwen在后台分析本页面。
2. 再单击浏览器右上角扩展程序栏的Qwen图标，便可以和Qwen交流当前页面的内容了。

注：阅读PDF文档为实验功能，尚不稳定。将在线PDF加入Qwen的阅读列表时，可能会因为网络问题、下载NLTK依赖等因素导致Qwen预处理时间较长，请耐心等待。建议先下载为本地PDF后，再在浏览器中打开本地PDF。

## 视频教学

可查看以下几个演示视频，了解BrowserQwen的基本操作：

- 根据浏览过的网页、PDFs进行长文创作 [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_write_article_based_on_webpages_and_pdfs.mp4)
- 提取浏览内容使用代码解释器画图 [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_chat_with_docs_and_code_interpreter.mp4)
- 上传文件、多轮对话利用代码解释器分析数据 [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_code_interpreter_multi_turn_chat.mp4)

# 评测基准

我们也开源了一个评测基准，用于评估一个模型写Python代码并使用Code Interpreter进行数学解题、数据分析、及其他通用任务时的表现。评测基准见 [benchmark](benchmark/README.md) 目录，当前的评测结果如下：

<table>
    <tr>
        <th colspan="4" align="center">生成代码的可执行率 (%)</th>
    </tr>
    <tr>
        <th align="center">Model</th><th align="center">Math↑</th><th align="center">Visualization↑</th><th align="center">General↑</th>
    </tr>
    <tr>
        <td>GPT-4</td><td align="center">91.9</td><td align="center">85.9</td><td align="center">82.8</td>
    </tr>
    <tr>
        <td>GPT-3.5</td><td align="center">89.2</td><td align="center">65.0</td><td align="center">74.1</td>
    </tr>
    <tr>
        <td>LLaMA2-7B-Chat</td>
        <td align="center">41.9</td>
        <td align="center">33.1</td>
        <td align="center">24.1 </td>
    </tr>
    <tr>
        <td>LLaMA2-13B-Chat</td>
        <td align="center">50.0</td>
        <td align="center">40.5</td>
        <td align="center">48.3 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-7B-Instruct</td>
        <td align="center">85.1</td>
        <td align="center">54.0</td>
        <td align="center">70.7 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-13B-Instruct</td>
        <td align="center">93.2</td>
        <td align="center">55.8</td>
        <td align="center">74.1 </td>
    </tr>
    <tr>
        <td>InternLM-7B-Chat-v1.1</td>
        <td align="center">78.4</td>
        <td align="center">44.2</td>
        <td align="center">62.1 </td>
    </tr>
    <tr>
        <td>InternLM-20B-Chat</td>
        <td align="center">70.3</td>
        <td align="center">44.2</td>
        <td align="center">65.5 </td>
    </tr>
    <tr>
        <td>Qwen-7B-Chat</td>
        <td align="center">82.4</td>
        <td align="center">64.4</td>
        <td align="center">67.2 </td>
    </tr>
    <tr>
        <td>Qwen-14B-Chat</td>
        <td align="center">89.2</td>
        <td align="center">84.1</td>
        <td align="center">65.5</td>
    </tr>
</table>

<table>
    <tr>
        <th colspan="4" align="center">代码执行结果的正确率 (%)</th>
    </tr>
    <tr>
        <th align="center">Model</th><th align="center">Math↑</th><th align="center">Visualization-Hard↑</th><th align="center">Visualization-Easy↑</th>
    </tr>
    <tr>
        <td>GPT-4</td><td align="center">82.8</td><td align="center">66.7</td><td align="center">60.8</td>
    </tr>
    <tr>
        <td>GPT-3.5</td><td align="center">47.3</td><td align="center">33.3</td><td align="center">55.7</td>
    </tr>
    <tr>
        <td>LLaMA2-7B-Chat</td>
        <td align="center">3.9</td>
        <td align="center">14.3</td>
        <td align="center">39.2 </td>
    </tr>
    <tr>
        <td>LLaMA2-13B-Chat</td>
        <td align="center">8.3</td>
        <td align="center">8.3</td>
        <td align="center">40.5 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-7B-Instruct</td>
        <td align="center">14.3</td>
        <td align="center">26.2</td>
        <td align="center">60.8 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-13B-Instruct</td>
        <td align="center">28.2</td>
        <td align="center">27.4</td>
        <td align="center">62.0 </td>
    </tr>
    <tr>
        <td>InternLM-7B-Chat-v1.1</td>
        <td align="center">28.5</td>
        <td align="center">4.8</td>
        <td align="center">40.5 </td>
    </tr>
    <tr>
        <td>InternLM-20B-Chat</td>
        <td align="center">34.6</td>
        <td align="center">21.4</td>
        <td align="center">45.6 </td>
    </tr>
    <tr>
        <td>Qwen-7B-Chat</td>
        <td align="center">41.9</td>
        <td align="center">40.5</td>
        <td align="center">54.4 </td>
    </tr>
    <tr>
        <td>Qwen-14B-Chat</td>
        <td align="center">58.4</td>
        <td align="center">53.6</td>
        <td align="center">59.5</td>
    </tr>
</table>

其中Qwen-7B-Chat指2023年09月25日后更新的版本。

# 免责声明

本项目并非正式产品，而是一个概念验证项目，用于演示Qwen系列模型的能力。
