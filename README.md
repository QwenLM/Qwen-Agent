[中文](./README_CN.md) ｜ English

<p align="center">
    <img src="https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/logo-qwen-agent.png" width="400"/>
<p>
<br>

Qwen-Agent is a framework for developing LLM applications based on the instruction following, tool usage, planning, and
memory capabilities of Qwen.
It also comes with example applications such as Browser Assistant, Code Interpreter, and Custom Assistant.

# Getting Started

## Installation

```bash
# Install dependencies.
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -e ./
```

## Preparation: Model Service

You can either use the model service provided
by [DashScope](https://help.aliyun.com/zh/dashscope/developer-reference/quick-start) from Alibaba Cloud, or deploy your
own model service using the open-source Qwen models.

If you want to use the model service provided by DashScope, please configure the environment variable:

```bash
# You need to replace YOUR_DASHSCOPE_API_KEY with your real DASHSCOPE_API_KEY.
export DASHSCOPE_API_KEY=YOUR_DASHSCOPE_API_KEY
````

If you want to deploy and use your own model service, please follow the instruction below, which is provided by
the <a href="https://github.com/QwenLM/Qwen">Qwen</a> project, to deploy a service compatible with the OpenAI API:

```bash
# Install dependencies.
git clone git@github.com:QwenLM/Qwen.git
cd Qwen
pip install -r requirements.txt
pip install fastapi uvicorn "openai<1.0.0" "pydantic>=2.3.0" sse_starlette

# Start the model service
#   -c to specify any open-source model listed at https://huggingface.co/Qwen
#   --server-name 0.0.0.0 allows other machines to access your service.
#   --server-name 127.0.0.1 only allows the machine deploying the model to access the service.
python openai_api.py --server-name 0.0.0.0 --server-port 7905 -c Qwen/Qwen-72B-Chat
```

## Developing Your Own Agent

Qwen-Agent provides atomic components such as LLMs and prompts, as well as high-level components such as Agents. The
example below uses the Assistant component as an illustration, demonstrating how to add custom tools and quickly develop
an agent that uses tools.

```py
import json
import json5
import urllib.parse
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool

llm_cfg = {
    # Use the model service provided by DashScope:
    'model': 'qwen-max',
    'model_server': 'dashscope',
    # Use your own model service compatible with OpenAI API:
    # 'model': 'Qwen',
    # 'model_server': 'http://127.0.0.1:7905/v1',

    # (Optional) LLM hyper-paramters:
    'generate_cfg': {
        'top_p': 0.8
    }
}
system = 'According to the user\'s request, you first draw a picture and then automatically run code to download the picture to image.jpg'


# Add a custom tool named my_image_gen：
@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    description = 'AI painting (image generation) service, input text description, and return the image URL drawn based on text information.'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': 'Detailed description of the desired image content, in English',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)


tools = ['my_image_gen', 'code_interpreter']  # code_interpreter is a built-in tool in Qwen-Agent
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

The framework also provides more atomic components for developers to combine. For additional showcases, please refer to
the [examples](./examples) directory.

# Example Application: BrowserQwen

We have also developed an example application based on Qwen-Agent: a **Chrome browser extension** called BrowserQwen,
which has key features such as:

- You can discuss with Qwen regarding the current webpage or PDF document.
- It records the web pages and PDF/Word/PowerPoint materials that you have browsed. It helps you understand multiple
  pages, summarize your browsing content, and automate writing tasks.
- It comes with plugin integration, including **Code Interpreter** for math problem solving and data visualization.

## BrowserQwen Demonstration

You can watch the following showcase videos to learn about the basic operations of BrowserQwen:

- Long-form writing based on visited webpages and
  PDFs. [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_write_article_based_on_webpages_and_pdfs.mp4)
- Drawing a plot using code interpreter based on the given
  information. [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_chat_with_docs_and_code_interpreter.mp4)
- Uploading files, multi-turn conversation, and data analysis using code
  interpreter. [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_code_interpreter_multi_turn_chat.mp4)

### Workstation - Editor Mode

**This mode is designed for creating long articles based on browsed web pages and PDFs.**

<figure>
    <img src="assets/screenshot-writing.png">
</figure>

**It allows you to call plugins to assist in rich text creation.**

<figure>
    <img src="assets/screenshot-editor-movie.png">
</figure>

### Workstation - Chat Mode

**In this mode, you can engage in multi-webpage QA.**

<figure >
    <img src="assets/screenshot-multi-web-qa.png">
</figure>

**Create data charts using the code interpreter.**

<figure>
    <img src="assets/screenshot-ci.png">
</figure>

### Browser Assistant

**Web page QA**

<figure>
    <img src="assets/screenshot-web-qa.png">
</figure>

**PDF document QA**

<figure>
    <img src="assets/screenshot-pdf-qa.png">
</figure>

## BrowserQwen User Guide

### Step 1. Deploy Local Database Service

On your local machine (the machine where you can open the Chrome browser), you will need to deploy a database service to
manage your browsing history and conversation history.

If you are using DashScope's model service, then please execute the following command:

```bash
# Start the database service, specifying the model on DashScope by using the --llm flag.
# The value of --llm can be one of the following, in increasing order of resource consumption:
#   - qwen-7b/14b/72b-chat (the same as the open-sourced 7B/14B/72B-Chat model)
#   - qwen-turbo, qwen-plus, qwen-max
# "YOUR_DASHSCOPE_API_KEY" is a placeholder. The user should replace it with their actual key.
python run_server.py --api_key YOUR_DASHSCOPE_API_KEY --model_server dashscope --llm qwen-max --workstation_port 7864
```

If you are using your own model service instead of DashScope, then please execute the following command:

```bash
# Start the database service, specifying the model service deployed with --model_server.
# If the IP address of the model service is 123.45.67.89,
#     you can specify --model_server http://123.45.67.89:7905/v1
# If the model service and the database service are on the same machine,
#     you can specify --model_server http://127.0.0.1:7905/v1
python run_server.py --model_server http://{MODEL_SERVER_IP}:7905/v1 --workstation_port 7864
```

Now you can access [http://127.0.0.1:7864/](http://127.0.0.1:7864/) to use the Workstation's Editor mode and Chat mode.

### Step 2. Install Browser Assistant

Install the BrowserQwen Chrome extension:

- Open the Chrome browser and enter `chrome://extensions/` in the address bar, then press Enter.
- Make sure that the `Developer mode` in the top right corner is turned on, then click on `Load unpacked` to upload
  the `browser_qwen` directory from this project and enable it.
- Click the extension icon in the top right corner of the Chrome browser to pin BrowserQwen to the toolbar.

Note that after installing the Chrome extension, you need to refresh the page for the extension to take effect.

When you want Qwen to read the content of the current webpage:

- Click the `Add to Qwen's Reading List` button on the screen to authorize Qwen to analyze the page in the background.
- Click the Qwen icon in the browser's top right corner to start interacting with Qwen about the current page's content.

# Evaluation Benchmark

We have also open-sourced a benchmark for evaluating the performance of a model in writing Python code and using Code
Interpreter for mathematical problem solving, data analysis, and other general tasks. The benchmark can be found in
the [benchmark](benchmark/README.md) directory. The current evaluation results are as follows:

<table>
    <tr>
        <th colspan="5" align="center">In-house Code Interpreter Benchmark (Version 20231206)</th>
    </tr>
    <tr>
        <th rowspan="2" align="center">Model</th>
        <th colspan="3" align="center">Accuracy of Code Execution Results (%)</th>
        <th colspan="1" align="center">Executable Rate of Code (%)</th>
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

# Disclaimer

This project is not intended to be an official product, rather it serves as a proof-of-concept project that highlights
the capabilities of the Qwen series models.

> Important: The code interpreter is not sandboxed, and it executes code in your own environment. Please do not ask Qwen
> to perform dangerous tasks, and do not directly use the code interpreter for production purposes.
