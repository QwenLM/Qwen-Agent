[中文](./README_CN.md) ｜ English

<p align="center">
    <img src="https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/logo-qwen-agent.png" width="400"/>
<p>
<br>

Qwen-Agent is a framework for harnessing the tool usage, planning, and memory capabilities of the open-source language model [Qwen](https://github.com/QwenLM/Qwen).
Building upon Qwen-Agent, we have developed a **Chrome browser extension** called BrowserQwen, which has key features such as:
- You can discuss with Qwen regarding the current webpage or PDF document.
- It records the web pages and PDF materials that you have browsed, with your permission. It helps you quickly understand the contents of multiple pages, summarize your browsing content, and eliminate tedious writing tasks.
- It supports plugin integration, including **Code Interpreter** for math problem solving and data visualization.
- It supports uploading PDF, Word, PPT and other types of documents for multi document Q&A.

# Use Case Demonstration

If you prefer watching videos instead of screenshots, you can refer to the [video demonstration](#video-demonstration).

## Workstation - Editor Mode

**This mode is designed for creating long articles based on browsed web pages and PDFs.**

<figure>
    <img src="assets/screenshot-writing.png">
</figure>

**It allows you to call plugins to assist in rich text creation.**

<figure>
    <img src="assets/screenshot-editor-movie.png">
</figure>

## Workstation - Chat Mode

**In this mode, you can engage in multi-webpage QA.**

<figure >
    <img src="assets/screenshot-multi-web-qa.png">
</figure>

**Create data charts using the code interpreter.**

<figure>
    <img src="assets/screenshot-ci.png">
</figure>

## Browser Assistant

**Web page QA**

<figure>
    <img src="assets/screenshot-web-qa.png">
</figure>

**PDF document QA**

<figure>
    <img src="assets/screenshot-pdf-qa.png">
</figure>

# BrowserQwen User Guide

Supported platforms: MacOS, Linux, Windows.

## Step 1. Deploy Model Service

***You can skip this step if you are using the model service provided by [DashScope](https://help.aliyun.com/zh/dashscope/developer-reference/quick-start) from Alibaba Cloud.***

However, if you prefer to deploy your own model service instead of using DashScope, please follow the instruction below, which is provided by the [Qwen](https://github.com/QwenLM/Qwen) project, to deploy a model service compatible with the OpenAI API:

```bash
# Install dependencies.
git clone git@github.com:QwenLM/Qwen.git
cd Qwen
pip install -r requirements.txt
pip install fastapi uvicorn openai "pydantic>=2.3.0" sse_starlette

# Start the model service, specifying the model version with the -c parameter.
# --server-name 0.0.0.0 allows other machines to access your service.
# --server-name 127.0.0.1 only allows the machine deploying the model to access the service.
python openai_api.py --server-name 0.0.0.0 --server-port 7905 -c QWen/QWen-14B-Chat
```

Currently, we can specify the -c argument with the following models, ordered in increasing GPU memory consumption:

- [`Qwen/Qwen-7B-Chat-Int4`](https://huggingface.co/Qwen/Qwen-7B-Chat-Int4)
- [`Qwen/Qwen-7B-Chat`](https://huggingface.co/Qwen/Qwen-7B-Chat-Int4)
- [`Qwen/Qwen-14B-Chat-Int4`](https://huggingface.co/Qwen/Qwen-14B-Chat-Int4)
- [`Qwen/Qwen-14B-Chat`](https://huggingface.co/Qwen/Qwen-14B-Chat)

For the 7B models, please use the versions pulled from the official HuggingFace repository after September 25, 2023, as both the code and model weights have changed.

## Step 2. Deploy Local Database Service

On your local machine (the machine where you can open the Chrome browser), you will need to deploy a database service to manage your browsing history and conversation history.

Please install the following dependencies if you have not done so already:

```bash
# Install dependencies.
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -r requirements.txt
```

If you have skipped Step 1 and decided to use DashScope's model service, then please execute the following command:

```bash
# Start the database service, specifying the model on DashScope by using the --llm flag.
# The value of --llm can be one of the following, in increasing order of resource consumption:
#   - qwen-7b-chat (the same as the open-sourced 7B-Chat model)
#   - qwen-14b-chat (the same as the open-sourced 14B-Chat model)
#   - qwen-turbo
#   - qwen-plus
# "YOUR_DASHSCOPE_API_KEY" is a placeholder. The user should replace it with their actual key.
python run_server.py --api_key YOUR_DASHSCOPE_API_KEY --model_server dashscope --llm qwen-7b-chat --workstation_port 7864
```

If you have followed Step 1 and are using your own model service instead of DashScope, then please execute the following command:

```bash
# Start the database service, specifying the model service deployed in Step 1 with --model_server.
# If the IP address of the machine in Step 1 is 123.45.67.89,
#     you can specify --model_server http://123.45.67.89:7905/v1
# If Step 1 and Step 2 are on the same machine,
#     you can specify --model_server http://127.0.0.1:7905/v1
python run_server.py --model_server http://{MODEL_SERVER_IP}:7905/v1 --workstation_port 7864
```

Now you can access [http://127.0.0.1:7864/](http://127.0.0.1:7864/) to use the Workstation's Editor mode and Chat mode.

For tips on using the Workstation, please refer to the instructions on the Workstation page or watch the [video demonstration](#video-demonstration).

## Step 3. Install Browser Assistant

Install the BrowserQwen Chrome extension:

- Open the Chrome browser and enter `chrome://extensions/` in the address bar, then press Enter.
- Make sure that the `Developer mode` in the top right corner is turned on, then click on `Load unpacked` to upload the `browser_qwen` directory from this project and enable it.
- Click the extension icon in the top right corner of the Chrome browser to pin BrowserQwen to the toolbar.

Note that after installing the Chrome extension, you need to refresh the page for the extension to take effect.

When you want Qwen to read the content of the current webpage:

- Click the `Add to Qwen's Reading List` button on the screen to authorize Qwen to analyze the page in the background.
- Click the Qwen icon in the browser's top right corner to start interacting with Qwen about the current page's content.

## Video Demonstration

You can watch the following showcase videos to learn about the basic operations of BrowserQwen:

- Long-form writing based on visited webpages and PDFs [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_write_article_based_on_webpages_and_pdfs.mp4)
- Drawing a plot using code interpreter based on the given information [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_chat_with_docs_and_code_interpreter.mp4)
- Uploading files, multi-turn conversation, and data analysis using code interpreter [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_code_interpreter_multi_turn_chat.mp4)

# Evaluation Benchmark

We have also open-sourced a benchmark for evaluating the performance of a model in writing Python code and using Code Interpreter for mathematical problem solving, data analysis, and other general tasks. The benchmark can be found in the [benchmark](benchmark/README.md) directory. The current evaluation results are as follows:

<table>
    <tr>
        <th colspan="4" align="center">Executable Rate of Generated Code (%)</th>
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
        <th colspan="4" align="center">Accuracy of Code Execution Results (%)</th>
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

Qwen-7B-Chat refers to the version updated after September 25, 2023.

# Disclaimer

This project is not intended to be an official product, rather it serves as a proof-of-concept project that highlights the capabilities of the Qwen series models.

> Important: The code interpreter is not sandboxed, and it executes code in your own environment. Please do not ask Qwen to perform dangerous tasks, and do not directly use the code interpreter for production purposes.
