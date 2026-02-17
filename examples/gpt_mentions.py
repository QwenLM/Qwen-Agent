# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A gpt @mentions gradio demo with stop button"""

import os
import re
import pprint
from typing import List

from qwen_agent.agents import Assistant, ReActChat
from qwen_agent.agents.doc_qa import BasicDocQA
from qwen_agent.agents.user_agent import PENDING_USER_INPUT
from qwen_agent.gui.gradio_dep import gr, mgr, ms
from qwen_agent.gui.utils import convert_fncall_to_text, convert_history_to_chatbot, get_avatar_image
from qwen_agent.gui.gradio_utils import format_cover_html
from qwen_agent.llm.schema import AUDIO, CONTENT, FILE, IMAGE, NAME, ROLE, USER, VIDEO, Message
from qwen_agent.log import logger
from qwen_agent.utils.utils import print_traceback


def init_agent_service():
    llm_cfg = {'model': 'qwen-max'}

    react_chat_agent = ReActChat(
        llm=llm_cfg,
        name='代码解释器',
        description='代码解释器，可用于执行Python代码。',
        system_message='you are a programming expert, skilled in writing code '
        'to solve mathematical problems and data analysis problems.',
        function_list=['code_interpreter'],
    )
    doc_qa_agent = BasicDocQA(
        llm=llm_cfg,
        name='文档问答',
        description='根据用户输入的问题和文档，从文档中找到答案',
    )

    assistant_agent = Assistant(llm=llm_cfg, name='小助理', description="I'm a helpful assistant")

    return [react_chat_agent, doc_qa_agent, assistant_agent]


# 全局变量存储agent信息
agent_list = []
user_config = {}
agent_config_list = []
verbose = True


def get_agent_index_by_name(agent_name):
    """根据agent名称获取索引"""
    if agent_name is None:
        return 0
    
    try:
        agent_name = agent_name.strip()
        for i, agent in enumerate(agent_list):
            if agent.name == agent_name:
                return i
        return 0
    except Exception:
        print_traceback()
        return 0


def add_text(_input, _audio_input, _chatbot, _history):
    """处理用户输入文本"""
    _history.append({
        ROLE: USER,
        CONTENT: [{
            'text': _input.text
        }],
    })

    if user_config.get(NAME):
        _history[-1][NAME] = user_config[NAME]
    
    # 处理音频输入
    if _audio_input:
        audio_input_file = gr.data_classes.FileData(path=_audio_input, mime_type="audio/wav")
        _input.files.append(audio_input_file)

    # 处理文件输入
    if _input.files:
        for file in _input.files:
            if file.mime_type.startswith('image/'):
                _history[-1][CONTENT].append({IMAGE: 'file://' + file.path})
            elif file.mime_type.startswith('audio/'):
                _history[-1][CONTENT].append({AUDIO: 'file://' + file.path})
            elif file.mime_type.startswith('video/'):
                _history[-1][CONTENT].append({VIDEO: 'file://' + file.path})
            else:
                _history[-1][CONTENT].append({FILE: file.path})

    _chatbot.append([_input, None])
    
    return gr.update(interactive=False, value=None), None, _chatbot, _history


def add_mention(_chatbot, _agent_selector):
    """处理@mentions功能"""
    if len(agent_list) == 1:
        return _chatbot, _agent_selector

    query = _chatbot[-1][0].text
    match = re.search(r'@\w+\b', query)
    if match:
        _agent_selector = get_agent_index_by_name(match.group()[1:])

    agent_name = agent_list[_agent_selector].name

    if ('@' + agent_name) not in query:
        _chatbot[-1][0].text = '@' + agent_name + ' ' + query

    return _chatbot, _agent_selector


def agent_run(_chatbot, _history, _agent_selector=None):
    """执行agent处理逻辑"""
    if verbose:
        logger.info('agent_run input:\n' + pprint.pformat(_history, indent=2))

    num_input_bubbles = len(_chatbot) - 1
    num_output_bubbles = 1
    _chatbot[-1][1] = [None for _ in range(len(agent_list))]

    agent_runner = agent_list[_agent_selector or 0]
    responses = []
    
    try:
        for responses in agent_runner.run(_history):
            if not responses:
                continue
            if responses[-1][CONTENT] == PENDING_USER_INPUT:
                logger.info('Interrupted. Waiting for user input!')
                break

            display_responses = convert_fncall_to_text(responses)
            if not display_responses:
                continue
            if display_responses[-1][CONTENT] is None:
                continue

            while len(display_responses) > num_output_bubbles:
                # 创建新的聊天气泡
                _chatbot.append([None, None])
                _chatbot[-1][1] = [None for _ in range(len(agent_list))]
                num_output_bubbles += 1

            assert num_output_bubbles == len(display_responses)
            assert num_input_bubbles + num_output_bubbles == len(_chatbot)

            for i, rsp in enumerate(display_responses):
                agent_index = get_agent_index_by_name(rsp[NAME])
                _chatbot[num_input_bubbles + i][1][agent_index] = rsp[CONTENT]

            if len(agent_list) > 1:
                _agent_selector = agent_index

            if _agent_selector is not None:
                yield _chatbot, _history, _agent_selector
            else:
                yield _chatbot, _history

        if responses:
            _history.extend([res for res in responses if res[CONTENT] != PENDING_USER_INPUT])

        if _agent_selector is not None:
            yield _chatbot, _history, _agent_selector
        else:
            yield _chatbot, _history

        if verbose:
            logger.info('agent_run response:\n' + pprint.pformat(responses, indent=2))
            
    except Exception as e:
        logger.error(f"Error in agent_run: {e}")
        print_traceback()
        if _agent_selector is not None:
            yield _chatbot, _history, _agent_selector
        else:
            yield _chatbot, _history


def flushed():
    """恢复输入框可交互状态"""
    return gr.update(interactive=True)


def change_agent(agent_selector):
    """切换agent时更新界面"""
    agent_config_interactive = agent_config_list[agent_selector]
    
    info_html = format_cover_html(
        bot_name=agent_config_interactive['name'],
        bot_description=agent_config_interactive['description'],
        bot_avatar=agent_config_interactive['avatar'],
    )
    
    agent_interactive = agent_list[agent_selector]
    if agent_interactive.function_map:
        capabilities = [key for key in agent_interactive.function_map.keys()]
        plugins = gr.update(
            value=capabilities,
            choices=capabilities,
        )
    else:
        plugins = gr.update(
            value=[],
            choices=[],
        )
    
    return agent_selector, info_html, plugins


def app_gui():
    """构建gradio界面"""
    global agent_list, user_config, agent_config_list
    
    # 初始化agent
    agent_list = init_agent_service()
    
    # 配置用户信息
    user_name = 'user'
    user_config = {
        'name': user_name,
        'avatar': get_avatar_image(user_name),
    }
    
    # 配置agent信息
    agent_config_list = [{
        'name': agent.name,
        'avatar': get_avatar_image(agent.name),
        'description': agent.description or "I'm a helpful assistant.",
    } for agent in agent_list]
    
    # 推荐对话
    prompt_suggestions = [
        '@代码解释器 2 ^ 10 = ?',
        '@文档问答 这篇论文解决了什么问题？',
        '@小助理 你好！',
    ]
    
    # 初始消息
    initial_messages = [{
        'role': 'assistant',
        'content': [{
            'text': '试试看 @代码解释器 来问我~'
        }]
    }]
    
    customTheme = gr.themes.Default(
        primary_hue=gr.themes.utils.colors.blue,
        radius_size=gr.themes.utils.sizes.radius_none,
    )

    with gr.Blocks(
        css=os.path.join(os.path.dirname(__file__), '..', 'qwen_agent', 'gui', 'assets', 'appBot.css'),
        theme=customTheme,
    ) as demo:
        history = gr.State([])
        
        with ms.Application():
            with gr.Row(elem_classes='container'):
                with gr.Column(scale=4):
                    chatbot = mgr.Chatbot(
                        value=convert_history_to_chatbot(messages=initial_messages),
                        avatar_images=[
                            user_config,
                            agent_config_list,
                        ],
                        height=850,
                        avatar_image_width=80,
                        flushing=False,
                        show_copy_button=True,
                        latex_delimiters=[{
                            'left': '\\(',
                            'right': '\\)',
                            'display': True
                        }, {
                            'left': '\\begin{equation}',
                            'right': '\\end{equation}',
                            'display': True
                        }, {
                            'left': '\\begin{align}',
                            'right': '\\end{align}',
                            'display': True
                        }, {
                            'left': '\\begin{alignat}',
                            'right': '\\end{alignat}',
                            'display': True
                        }, {
                            'left': '\\begin{gather}',
                            'right': '\\end{gather}',
                            'display': True
                        }, {
                            'left': '\\begin{CD}',
                            'right': '\\end{CD}',
                            'display': True
                        }, {
                            'left': '\\[',
                            'right': '\\]',
                            'display': True
                        }]
                    )

                    with gr.Row():
                        with gr.Column(scale=7):
                            input_box = mgr.MultimodalInput(placeholder='跟我聊聊吧～')
                        with gr.Column(scale=1, min_width=0):
                            stop_bt = gr.Button('🚫')
                    
                    audio_input = gr.Audio(
                        sources=["microphone"],
                        type="filepath"
                    )

                with gr.Column(scale=1):
                    if len(agent_list) > 1:
                        agent_selector = gr.Dropdown(
                            [(agent.name, i) for i, agent in enumerate(agent_list)],
                            label='Agents',
                            info='选择一个Agent',
                            value=0,
                            interactive=True,
                        )
                    else:
                        agent_selector = gr.State(0)

                    # Agent信息显示
                    agent_info_block = gr.HTML(
                        format_cover_html(
                            bot_name=agent_config_list[0]['name'],
                            bot_description=agent_config_list[0]['description'],
                            bot_avatar=agent_config_list[0]['avatar'],
                        )
                    )

                    # Agent插件显示
                    agent_interactive = agent_list[0]
                    if agent_interactive.function_map:
                        capabilities = [key for key in agent_interactive.function_map.keys()]
                        agent_plugins_block = gr.CheckboxGroup(
                            label='插件',
                            value=capabilities,
                            choices=capabilities,
                            interactive=False,
                        )
                    else:
                        agent_plugins_block = gr.CheckboxGroup(
                            label='插件',
                            value=[],
                            choices=[],
                            interactive=False,
                        )

                    if prompt_suggestions:
                        gr.Examples(
                            label='推荐对话',
                            examples=prompt_suggestions,
                            inputs=[input_box],
                        )

            # 事件绑定
            if len(agent_list) > 1:
                agent_selector.change(
                    fn=change_agent,
                    inputs=[agent_selector],
                    outputs=[agent_selector, agent_info_block, agent_plugins_block],
                    queue=False,
                )

            # 处理输入提交
            input_promise = input_box.submit(
                fn=add_text,
                inputs=[input_box, audio_input, chatbot, history],
                outputs=[input_box, audio_input, chatbot, history],
                queue=False,
            )

            # 处理mentions和agent运行
            if len(agent_list) > 1:
                input_promise = input_promise.then(
                    add_mention,
                    [chatbot, agent_selector],
                    [chatbot, agent_selector],
                ).then(
                    agent_run,
                    [chatbot, history, agent_selector],
                    [chatbot, history, agent_selector],
                )
            else:
                input_promise = input_promise.then(
                    agent_run,
                    [chatbot, history],
                    [chatbot, history],
                )

            # 恢复输入框状态
            input_promise.then(flushed, None, [input_box])
            
            # 停止按钮功能
            stop_bt.click(None, None, None, cancels=[input_promise], queue=False)

        demo.load(None)

    demo.queue(default_concurrency_limit=10).launch(share=False)


if __name__ == '__main__':
    app_gui()
