import json
import os
import time
from pathlib import Path

import jsonlines

try:
    import add_qwen_libs  # NOQA
except ImportError:
    pass

from qwen_agent.agents import Assistant
from qwen_agent.gui import gr
from qwen_agent.gui.utils import get_avatar_image
from qwen_agent.llm.base import ModelServiceError
from qwen_agent.log import logger
from qwen_server.schema import GlobalConfig
from qwen_server.utils import read_history, read_meta_data_by_condition, save_history

server_config_path = Path(__file__).resolve().parent / 'server_config.json'
with open(server_config_path, 'r') as f:
    server_config = json.load(f)
    server_config = GlobalConfig(**server_config)

llm_config = None

if hasattr(server_config.server, 'llm'):
    llm_config = {
        'model': server_config.server.llm,
        'api_key': server_config.server.api_key,
        'model_server': server_config.server.model_server
    }

assistant = Assistant(llm=llm_config)

with open(Path(__file__).resolve().parent / 'css/main.css', 'r') as f:
    css = f.read()
with open(Path(__file__).resolve().parent / 'js/main.js', 'r') as f:
    js = f.read()
cache_file_popup_url = os.path.join(server_config.path.work_space_root, 'popup_url.jsonl')
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
        # Only able to remind the situation of first browsing failure
        gr.Error('Oops, it seems that the page cannot be opened due to network issues.')

    for line in jsonlines.open(cache_file_popup_url):
        lines.append(line)
    logger.info('The current access page is: ' + lines[-1]['url'])
    return lines[-1]['url']


def bot(history):
    page_url = set_url()
    if not history:
        yield history
    else:
        messages = [{'role': 'user', 'content': [{'text': history[-1][0]}, {'file': page_url}]}]
        history[-1][1] = ''
        try:
            response = assistant.run(messages=messages, max_ref_token=server_config.server.max_ref_token)
            for rsp in response:
                if rsp:
                    history[-1][1] = rsp[-1]['content']
                    yield history
        except ModelServiceError as ex:
            history[-1][1] = str(ex)
            yield history
        except Exception as ex:
            raise ValueError(ex)

        save_history(history, page_url, history_dir)


def init_chatbot():
    time.sleep(1)
    page_url = set_url()
    response = read_meta_data_by_condition(meta_file, url=page_url)
    if not response:
        gr.Info(
            "Please add this page to Qwen's Reading List first! If you have already added it, please reopen later...")
    elif response == '[CACHING]':
        gr.Info('Please reopen later, Qwen is analyzing this page...')
    else:
        return read_history(page_url, history_dir)


def clear_session():
    page_url = set_url()
    save_history(None, page_url, history_dir)
    return None


with gr.Blocks(css=css, theme='soft') as demo:
    chatbot = gr.Chatbot([], elem_id='chatbot', height=480, avatar_images=(None, get_avatar_image('qwen')))
    with gr.Row():
        with gr.Column(scale=7):
            txt = gr.Textbox(show_label=False, placeholder='Chat with Qwen...', container=False)
        with gr.Column(scale=1, min_width=0):
            clr_bt = gr.Button('🧹', elem_classes='bt_small_font')
        with gr.Column(scale=1, min_width=0):
            stop_bt = gr.Button('🚫', elem_classes='bt_small_font')
        with gr.Column(scale=1, min_width=0):
            re_bt = gr.Button('🔁', elem_classes='bt_small_font')

    txt_msg = txt.submit(add_text, [chatbot, txt], [chatbot, txt], queue=False).then(bot, chatbot, chatbot)
    txt_msg.then(lambda: gr.update(interactive=True), None, [txt], queue=False)

    clr_bt.click(clear_session, None, chatbot, queue=False)
    re_txt_msg = re_bt.click(rm_text, [chatbot], [chatbot, txt], queue=False).then(bot, chatbot, chatbot)
    re_txt_msg.then(lambda: gr.update(interactive=True), None, [txt], queue=False)

    stop_bt.click(None, None, None, cancels=[txt_msg, re_txt_msg], queue=False)

    demo.load(init_chatbot, None, chatbot)

demo.queue().launch(server_name=server_config.server.server_host, server_port=server_config.server.app_in_browser_port)
