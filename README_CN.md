# Qwen-Agent
中文 ｜ [English](./README.md)

Qwen-Agent是基于通义千问（Qwen），将插件使用、规划生成、动作执行等组件集合起来的一个代码库。目前我们实现了一个浏览器扩展程序BrowserQwen，便捷的辅助您实现网页&PDF理解、知识整合与内容编辑工作。BrowserQwen的特点包括：
- 将Qwen集成到浏览器扩展程序，支持在浏览器中和Qwen讨论打开的Web页面和PDF文档(在线文档或本地文档)。
- 在您允许的前提下，Qwen将记录您浏览过的网页&PDFs素材，辅助您依据浏览内容完成编辑工作。通过它，您可以快速完成多网页内容理解、浏览内容整理、新文章撰写等繁琐的工作。
- 支持插件调用，目前已集成Code Interpreter、搜索等插件。

# 用例演示
## 浏览器交互界面问答

<div style="display:flex;">
    <figure style="width:45%;">
        <img src="assets/screenshot-pdf-qa.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">PDF文档问答</figcaption>
    </figure>
    <figure style="width:45%;">
        <img src="assets/screenshot-web-qa.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">网页问答</figcaption>
    </figure>
</div>

## 编辑工作台
<div style="display:flex;">
    <figure>
        <img src="assets/screenshot-writing.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">根据浏览过的网页、PDFs素材进行长文创作</figcaption>
    </figure>
    <figure>
        <img src="assets/screenshot-editor-movie.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">调用插件辅助创作</figcaption>
    </figure>
</div>

<div style="display:flex;">
    <figure >
        <img src="assets/screenshot-multi-web-qa.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">多网页问答</figcaption>
    </figure>
    <figure>
        <img src="assets/screenshot-ci.png" alt="paper-attention-qa">
        <figcaption style="text-align:center;">使用代码解释器画图</figcaption>
    </figure>
</div>

# BrowserQwen 快速使用

## 安装环境
```
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -r requirements.txt
```

## 启动服务
### 启动Qwen: 参考[Qwen-7B](https://github.com/QwenLM/Qwen-7B/blob/main/README_CN.md#api)中OpenAI API部署方法:
```
python openai_api.py --server-port 7905
```

### 启动浏览器扩展程序后台服务&编辑工作台服务:
```
python run_server.py --model_server http://127.0.0.1:7905/v1
```
- ```model_server```参数是上面启动的Qwen服务的地址，默认为```http://127.0.0.1:7905/v1```，依据实际需求更改
- ```Ctrl+C```可以关闭服务

### 上传浏览器扩展程序
- 进入[谷歌扩展程序](chrome://extensions/)界面
- 点击【加载已解压的扩展程序】，在文件目录中找到```browser_qwen```路径，上传并启用
- 单击谷歌浏览器右上角```扩展程序```图标，将BrowserQwen固定在工具栏
- 打开插件后，需要刷新页面，插件才能生效

## 使用提示
- 在觉得浏览网页内容有用时，点击屏幕右上方的```Add to Qwen's Reading List```按钮，通义千问将在后台分析本页面（考虑到用户隐私，必须先点击按钮授权后，Qwen才能阅读本页内容）
- 单击右上角通义千问图标，和通义千问交流当前浏览页面
- 访问默认地址```http://127.0.0.1:7864/```进入编辑工作台，通义千问依据浏览记录辅助您完成编辑
- 编辑页面主要包含三个区域：
    - Browsing History：
        - Start Date / End Date：选择需要的时间段的浏览资料，包含起始日和结束日
        - 浏览资料列表：支持选中或去除具体浏览记录
    - Editor：编辑区，在```Input```模块编辑内容或输入指令，点击```Continue```按钮让Qwen辅助完成编辑工作
        - 输入内容后直接点击```Continue```按钮：Qwen根据浏览资料完成续写
        - 使用特殊指令：
            - /title + 内容：Qwen启用内置planning流程，撰写一整篇文稿
            - /code + 内容：Qwen启用code interpreter插件，撰写并运行python代码，生成回复
            - /plug + 内容：Qwen启用plug-in，选择合适的插件生成回复
    - Chat：交互区，Qwen根据给定的参考资料，生成回复；勾选Code Interpreter后启用代码解释器插件


# 代码结构
- qwen_agent
    - agents: 存放planning/tools/action/memory等通用的方法实现
    - llm: 定义访问大模型的接口，目前提供了Qwen的OpenAI格式访问接口
    - configs：存放配置文件，可以在这里修改本地服务端口等配置
- browser_qwen: 存放BrowserQwen的实现，包括谷歌扩展配置、前端界面和后台处理逻辑


## 参数定制
该库支持自定义参数，必要参数在```qwen_agent/configs/config_browserqwen.py```中设置，常用参数如下：
- llm：使用的大模型，支持OpenAI API格式，默认使用```Qwen-7B-Chat```
- MAX_TOKEN：限制参考资料的最大token数，默认```4000```，如果LLM支持较长的Token，可以扩大该数值
- fast_api_host、app_host、app_in_browser_host：后台服务的地址，默认均为本地```127.0.0.1```
- 注意：修改配置文件或代码后需要重启服务才能起效
