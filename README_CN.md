# Qwen-Agent
中文 ｜ [English](./README.md)

Qwen-Agent是基于大模型，将插件使用、规划生成、动作执行等组件集合起来的一个代码库。目前我们实现了一个谷歌扩展BrowserQwen，便捷的辅助您实现知识整合与内容编辑工作。BrowserQwen的特点包括：
- 它可以在您允许的前提下，记录您的网页浏览内容，并采用通义千问作为分析助手，辅助您依据浏览内容完成编辑工作。通过它，您可以快速完成网页内容理解、浏览内容整理、新文章撰写等繁琐的工作。
- 支持对打开的PDF文档(在线文档或本地文档)进行分析，您可以在浏览器打开PDF文档，并通过通义千问实现文档的快速理解。
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

- 可以在```examples```文件夹下查看生成的文稿示例

# BrowserQwen 快速使用

## 安装环境
```
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -r requirements.txt
```

## 参数配置
- 必要参数在```configs/config_browserqwen.py```中设置，常用参数如下：
    - llm：使用的大模型，支持OpenAI API格式，默认使用```Qwen-7B-Chat```
    - MAX_TOKEN：限制参考资料的最大token数，默认```5000```
    - fast_api_host、app_host、app_in_browser_host：后台服务的地址和端口，默认均为本地```127.0.0.1```


## 启动服务
### 启动Qwen: 参考[Qwen-7B](https://github.com/QwenLM/Qwen-7B/blob/main/README_CN.md#api)中OpenAI API部署方法:
```
python openai_api.py --server-port 8003
```
- 部署好Qwen后，修改```qwen_agent/llm/qwen.py```中的```openai.api_base```为对应的地址和端口，默认为```http://127.0.0.1:7905/v1```

### 启动谷歌扩展后台服务&编辑工作台:
```
python run_server.py
```
- ```Ctrl+C```可以关闭服务
- 修改配置文件或代码后需要重启服务才能起效

### 上传至谷歌扩展
- 进入[谷歌扩展](chrome://extensions/)界面
- 点击【加载已解压的扩展程序】，在文件目录中找到```browser_qwen```路径，上传并启用
- 单击谷歌浏览器右上角```扩展程序```图标，将BrowserQwen固定在工具栏
- 打开插件后，需要刷新页面，插件才能生效

## 使用提示
- 在觉得浏览网页内容有用时，点击屏幕右上方的```Add to Qwen's Reading List```按钮，通义千问将在后台分析本页面（考虑到用户隐私，必须先点击按钮授权后，Qwen才能阅读本页内容）
- 单击右上角通义千问图标，和通义千问交流当前浏览页面
- 访问默认地址```http://127.0.0.1:7864/```进入编辑工作台，通义千问依据浏览记录辅助您完成编辑
- 编辑页面如下图，主要包含五个区域：
    - Start Date / End Date：选择需要的时间段的浏览资料，包含起始日和结束日
    - Browser List：浏览资料列表，支持选中或去除具体浏览内容；支持手动添加URL到浏览列表
    - Recommended Topics：Qwen根据浏览资料生成的推荐的话题，支持重新生成
    - Editor：编辑区，在```Input```模块编辑内容或输入指令，点击```Continue```按钮让Qwen辅助完成编辑工作
        - 输入内容后直接点击```Continue```按钮：Qwen根据浏览资料完成续写
        - 使用特殊指令：
            - /title + 内容：Qwen启用内置planning流程，撰写一整篇文稿
            - /code + 内容：Qwen启用code interpreter插件，撰写并运行python代码，生成回复
            - /plug + 内容：Qwen启用plug-in，选择合适的插件生成回复
    - Chat：交互区，Qwen根据给定的参考资料，生成回复；勾选CI后启用code interpreter插件，支持上传文件进行数据分析


# 代码结构
- qwen_agent
    - agents: 存放planning/tools/action/memory等通用的方法实现
    - llm: 定义访问大模型的接口，目前提供了Qwen的OpenAI格式访问接口
    - configs：存放配置文件，可以在这里修改本地服务端口等配置
- browser_qwen: 存放BrowserQwen的实现，包括谷歌扩展配置、前端界面和后台处理逻辑
