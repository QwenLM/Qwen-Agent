import json
import os
import time
from pathlib import Path

import add_qwen_libs  # NOQA
import gradio as gr
import jsonlines

from qwen_agent.agents import DocQAAgent
from qwen_agent.llm.base import ModelServiceError
from qwen_agent.log import logger
from qwen_server import output_beautify
from qwen_server.schema import GlobalConfig
from qwen_server.utils import (read_history, read_meta_data_by_condition,
                               save_history)

server_config_path = Path(__file__).resolve().parent / 'server_config.json'
with open(server_config_path, 'r') as f:
    server_config = json.load(f)
    server_config = GlobalConfig(**server_config)

function_list = None
llm_config = None
storage_path = None

if hasattr(server_config.server, 'llm'):
    llm_config = {
        'model': server_config.server.llm,
        'api_key': server_config.server.api_key,
        'model_server': server_config.server.model_server
    }
if hasattr(server_config.server, 'functions'):
    function_list = server_config.server.functions
if hasattr(server_config.path, 'database_root'):
    storage_path = server_config.path.database_root

assistant = DocQAAgent(function_list=function_list, llm=llm_config)

with open(Path(__file__).resolve().parent / 'css/main.css', 'r') as f:
    css = f.read()
with open(Path(__file__).resolve().parent / 'js/main.js', 'r') as f:
    js = f.read()
cache_file_popup_url = os.path.join(server_config.path.work_space_root,
                                    'popup_url.jsonl')
meta_file = os.path.join(server_config.path.work_space_root, 'meta_data.jsonl')
history_dir = os.path.join(server_config.path.work_space_root, 'history')


def add_text(history, text):
    history = history + [(text, None)]
    return history, gr.update(value='', interactive=False)


def rm_text(history):
    if not history:
        gr.Warning('No input content!')
    elif not history[-1][1]:
        return history, gr.update(value='', interactive=False)
    else:
        history = history[:-1] + [(history[-1][0], None)]
        return history, gr.update(value='', interactive=False)


def set_url():
    lines = []
    if not os.path.exists(cache_file_popup_url):
        gr.Error('Do not add any pages!')
    assert os.path.exists(cache_file_popup_url)
    for line in jsonlines.open(cache_file_popup_url):
        lines.append(line)
    logger.info('The current access page is: ' + lines[-1]['url'])
    return lines[-1]['url']


def bot(history):
    page_url = set_url()
    if not history:
        yield history
    else:
        messages = [{
            'role': 'user',
            'content': [{
                'text': history[-1][0]
            }, {
                'file': page_url
            }]
        }]
        history[-1][1] = ''
        try:
            response = assistant.run(
                messages=messages,
                max_ref_token=server_config.server.max_ref_token)

            for chunk in output_beautify.convert_to_full_str_stream(response):
                history[-1][1] = chunk
                yield history
        except ModelServiceError:
            history[-1][1] = '模型调用出错，可能的原因有：未正确配置模型参数，或输入数据不安全等'
            yield history
        except Exception as ex:
            raise ValueError(ex)

        save_history(history, page_url, history_dir)


def init_chatbot():
    time.sleep(0.5)
    page_url = set_url()
    response = read_meta_data_by_condition(meta_file, url=page_url)
    if not response:
        gr.Info("Please add this page to Qwen's Reading List first!")
    elif response == '[CACHING]':
        gr.Info('Please reopen later, Qwen is analyzing this page...')
    else:
        return read_history(page_url, history_dir)


def clear_session(history):
    page_url = set_url()
    save_history(None, page_url, history_dir)
    return None


with gr.Blocks(css=css, theme='soft') as demo:
    chatbot = gr.Chatbot([],
                         elem_id='chatbot',
                         height=480,
                         avatar_images=(None, (os.path.join(
                             Path(__file__).resolve().parent,
                             'img/logo.png'))))
    with gr.Row():
        with gr.Column(scale=7):
            txt = gr.Textbox(show_label=False,
                             placeholder='Chat with Qwen...',
                             container=False)
        with gr.Column(scale=1, min_width=0):
            clr_bt = gr.Button('🧹', elem_classes='bt_small_font')
        with gr.Column(scale=1, min_width=0):
            stop_bt = gr.Button('🚫', elem_classes='bt_small_font')
        with gr.Column(scale=1, min_width=0):
            re_bt = gr.Button('🔁', elem_classes='bt_small_font')

    txt_msg = txt.submit(add_text, [chatbot, txt], [chatbot, txt],
                         queue=False).then(bot, chatbot, chatbot)
    txt_msg.then(lambda: gr.update(interactive=True), None, [txt], queue=False)

    clr_bt.click(clear_session, None, chatbot, queue=False)
    re_txt_msg = re_bt.click(rm_text, [chatbot], [chatbot, txt],
                             queue=False).then(bot, chatbot, chatbot)
    re_txt_msg.then(lambda: gr.update(interactive=True),
                    None, [txt],
                    queue=False)

    stop_bt.click(None, None, None, cancels=[txt_msg, re_txt_msg], queue=False)

    demo.load(init_chatbot, None, chatbot)

demo.queue().launch(server_name=server_config.server.server_host,
                    server_port=server_config.server.app_in_browser_port)
