# Qwen-Agent
[中文](./README_CN.md) ｜ English

Qwen-Agent is a code library based on Qwen (abbr. Tongyi Qianwen) that integrates components such as plugin usage, planning generation, and action execution. At present, we have implemented a Google Extension ```BrowserQwen``` to facilitate your knowledge integration and content editing work. The features of BrowserQwen include:

- Integrate Qwen into the Google Extension, supporting discussion of Webpages and PDF documents (online or local) with Qwen in the browser.
- Qwen can record your webpage browsing history and PDFs with your permission, and assist you in completing editing work. Through it, you can quickly complete tedious tasks such as understanding web content, organizing browsing history, and writing new articles.
- Supporting plugin calls, and currently integrating plugins such as Code Interpreter and Google Search.

# Demonstration
## Q&A in Browser Interactive Interface

<div style="display:flex;">
    <figure style="width:45%;">
        <img src="assets/screenshot-pdf-qa.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">Question Answering over a PDF</figcaption>
    </figure>
    <figure style="width:45%;">
        <img src="assets/screenshot-web-qa.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">Question Answering over a Webpage</figcaption>
    </figure>
</div>

## Editing Workstation
<div style="display:flex;">
    <figure>
        <img src="assets/screenshot-writing.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">Writing Articles based on Browsed Webpages and PDFs</figcaption>
    </figure>
    <figure>
        <img src="assets/screenshot-editor-movie.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">Calling Plugins to Assist in Writing</figcaption>
    </figure>
</div>

<div style="display:flex;">
    <figure>
        <img src="assets/screenshot-multi-web-qa.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">Question Answering over Multiple Webpages</figcaption>
    </figure>
    <figure>
        <img src="assets/screenshot-ci.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">Ask Qwen to draw Figures by Code Interpreter</figcaption>
    </figure>
</div>

# How to use BrowserQwen

## Quick Start
```
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -r requirements.txt
```

## Start Service
### Start Qwen: Refer to the OpenAI API deployment method in [Qwen-7B](https://github.com/QwenLM/Qwen-7B/blob/main/README.md#api):

```
python openai_api.py --server-port 7905
```

### Start the Backend Services of Google Extension and Editing Workstation:
```
python run_server.py --model_server http://127.0.0.1:7905/v1
```
- model_server is the address of Qwen's OpenAI API Interface, default to ```http://127.0.0.1:7905/v1```
- Pressing ```Ctrl+C``` can close the service


### Upload to Google Extension
- Entering [Google Extension](chrome://extensions/)
- Finding file ```browser_qwen```, uploading and enabling
- Clicking on the Google Chrome Extensions icon in the top right corner of Google Chrome to pin BrowserQwen in the toolbar

### Usage Tips
- When you find browsing web content useful, click the ```Add to Qwen's Reading List``` button in the upper right corner of the screen, and Qwen will analyze this page in the background. (Considering user privacy, user must first click on the button to authorize Qwen before reading this page)
- Clicking on the Qwen icon in the upper right corner to communicate with Qwen on the current browsing page.
- Accessing the default address```http://127.0.0.1:7864/``` to work on the editing workstation and Qwen will assist you with editing based on browsing records.

- The editing workstation mainly consists of three areas:
    - Browser List:
        - Start Date/End Date: Selecting the browsed materials for the desired time period, including the start and end dates
        - The browsed materials list: supporting the selection or removal of specific browsing content
    - Editor: In the editing area, you can directly input content or special instructions, and then click the ```Continue``` button to have Qwen assist in completing the editing work:
        - After inputting the content, directly click the ```Continue``` button: Qwen will begin to continue writing based on the browsing information
        - Using special instructions:
            - /title + content: Qwen enables the built-in planning process and writes a complete manuscript
            - /code + content: Qwen enables the code interpreter plugin, writes and runs Python code, and generates replies
            - /plug + content: Qwen enables plugin and select appropriate plugin to generate reply
    - Chat: Interactive area. Qwen generates replies based on given reference materials. Selecting Code Interpreter will enable the code interpreter plugin

# Code structure

- qwen_agent
    - agents: The implementation of general methods for planning/tools/actions/memory
    - llm: Defining the interface for accessing LLM, currently providing OpenAI format access interface for Qwen-7B
    - configs: Storing the configuration files where you can modify local service ports and other configurations
- browser_qwen: The implementation of BrowserQwen, including google extension configuration, front-end interface, and backend processing logic

## Configuration
This library supports custom parameters. Setting necessary parameters in ```configs/config_browserqwen.py```, commonly used parameters are as follows:
- llm: The large model. Now supporting OpenAI API format, default to ```Qwen-7B-Chat```.
- MAX_TOKEN：The maximum number of tokens for reference materials, default to ```4000```. If LLM supports longer tokens, this value can be expanded.
- fast_api_host、app_host、app_in_browser_host：The address of the backend service, default to ```127.0.0.1```
- Note: After modifying the configuration file or code, the service need to be restarted to take effect.
