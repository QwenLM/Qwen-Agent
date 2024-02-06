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

You can either use the model service provided by Alibaba Cloud's [DashScope](https://help.aliyun.com/zh/dashscope/developer-reference/quick-start), or deploy and use your own model service using the open-source Qwen models.

If you choose to use the model service offered by DashScope, please ensure that you set the environment variable `DASHSCOPE_API_KEY` to your unique DashScope API key.

Alternatively, if you prefer to deploy and utilize your own model service, kindly follow the instructions outlined in the [Deployment](https://github.com/QwenLM/Qwen1.5?tab=readme-ov-file#deployment) section of Qwen1.5's README to start an OpenAI-compatible API service.

## Developing Your Own Agent

Qwen-Agent provides atomic components such as LLMs and prompts, as well as high-level components such as Agents. The
example below uses the Assistant component as an illustration, demonstrating how to add custom tools and quickly develop
an agent that uses tools.

```py
import json
import os

import json5
import urllib.parse
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool

llm_cfg = {
    # Use the model service provided by DashScope:
    'model': 'qwen-max',
    'model_server': 'dashscope',
    # 'api_key': 'YOUR_DASHSCOPE_API_KEY',
    # It will use the `DASHSCOPE_API_KEY' environment variable if 'api_key' is not set here.

    # Use your own model service compatible with OpenAI API:
    # 'model': 'Qwen/Qwen1.5-72B-Chat',
    # 'model_server': 'http://localhost:8000/v1',  # api_base
    # 'api_key': 'EMPTY',

    # (Optional) LLM hyperparameters for generation:
    'generate_cfg': {
        'top_p': 0.8
    }
}
system = 'According to the user\'s request, you first draw a picture and then automatically run code to download the picture ' + \
          'and select an image operation from the given document to process the image'

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
bot = Assistant(llm=llm_cfg,
                system_message=system,
                function_list=tools,
                files=[os.path.abspath('doc.pdf')])

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
#   - qwen1.5-7b/14b/72b-chat (the same as the open-sourced Qwen1.5 7B/14B/72B Chat model)
#   - qwen-turbo, qwen-plus, qwen-max (qwen-max is recommended)
# "YOUR_DASHSCOPE_API_KEY" is a placeholder. The user should replace it with their actual key.
python run_server.py --llm qwen-max --model_server dashscope --workstation_port 7864 --api_key YOUR_DASHSCOPE_API_KEY
```

If you are using your own model service instead of DashScope, then please execute the following command:

```bash
# Specify the model service, and start the database service.
# Example: Assuming Qwen/Qwen1.5-72B-Chat is deployed at http://localhost:8000 using vLLM, you can specify the model service as:
#   --llm Qwen/Qwen1.5-72B-Chat --model_server http://localhost:8000/v1 --api_key EMPTY
python run_server.py --llm {MODEL} --model_server {API_BASE} --workstation_port 7864 --api_key {API_KEY}
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

# Disclaimer

This project is currently under active development, and backward compatibility may occasionally be broken.

> Important: The code interpreter is not sandboxed, and it executes code in your own environment. Please do not ask Qwen
> to perform dangerous tasks, and do not directly use the code interpreter for production purposes.
