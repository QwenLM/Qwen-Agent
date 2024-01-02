import json
import os
from pathlib import Path

import add_qwen_libs  # NOQA
import gradio as gr
import json5

from qwen_agent.agents import DocQAAgent
from qwen_agent.log import logger
from qwen_server.schema import GlobalConfig

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

assistant = DocQAAgent(function_list=function_list,
                       llm=llm_config,
                       storage_path=storage_path)

with open(Path(__file__).resolve().parent / 'css/main.css', 'r') as f:
    css = f.read()
with open(Path(__file__).resolve().parent / 'js/main.js', 'r') as f:
    js = f.read()


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
    url = assistant.mem.db.get('browsing_url', re_load=True)
    logger.info('The current access url is: ' + url)
    return url


def read_content(url):
    return assistant.mem.db.get(url)


def save_history(history, url):
    history = history or []
    content = json5.loads(read_content(url))
    content['session'] = history
    assistant.mem.db.put(url, json.dumps(content, ensure_ascii=False))


def bot(history):
    page_url = set_url()
    if not history:
        yield history
    else:
        query = history[-1][0]
        history[-1][1] = ''
        if len(history) > 1:
            chat_history = history[:-1]
        else:
            chat_history = None
        response = assistant.run(
            query,
            page_url,
            max_ref_token=server_config.server.max_ref_token,
            history=chat_history)
        if response == 'Not Exist':
            gr.Info("Please add this page to Qwen's Reading List first!")
        elif response == 'Empty':
            gr.Info('Please reopen later, Qwen is analyzing this page...')
        else:
            for chunk in response:
                history[-1][1] += chunk
                yield history
            save_history(history, page_url)


def load_history_session():
    page_url = set_url()
    response = read_content(page_url)
    if response == 'Not Exist':
        gr.Info("Please add this page to Qwen's Reading List first!")
    elif response == '':
        gr.Info('Please reopen later, Qwen is analyzing this page...')
    else:
        return json5.loads(response)['session']


def clear_session(history):
    page_url = set_url()
    if not history:
        return None
    save_history(None, page_url)
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

    demo.load(load_history_session, None, chatbot)

demo.queue().launch(server_name=server_config.server.server_host,
                    server_port=server_config.server.app_in_browser_port)
