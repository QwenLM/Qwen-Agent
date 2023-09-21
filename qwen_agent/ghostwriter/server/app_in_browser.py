import importlib
import json
import os
import sys
from pathlib import Path

import gradio as gr
import jsonlines

sys.path.insert(
    0,
    str(Path(__file__).absolute().parent.parent.parent.parent))  # NOQA

from qwen_agent.agents.actions import Simple  # NOQA
from qwen_agent.configs.config_ghostwriter import cache_root  # NOQA
from qwen_agent.configs import config_ghostwriter  # NOQA
from qwen_agent.agents.tools.similarity_search import SimilaritySearch  # NOQA
from qwen_agent.agents.memory import Memory  # NOQA

if config_ghostwriter.llm.startswith('gpt'):
    module = 'qwen_agent.llm.gpt'
    llm = importlib.import_module(module).GPT(config_ghostwriter.llm)
elif config_ghostwriter.llm.startswith('Qwen'):
    module = 'qwen_agent.llm.qwen'
    llm = importlib.import_module(module).Qwen(config_ghostwriter.llm)
else:
    llm = None

mem = Memory(config_ghostwriter.similarity_search, config_ghostwriter.similarity_search_type)

if not os.path.exists(cache_root):
    os.makedirs(cache_root)
cache_file = os.path.join(cache_root, config_ghostwriter.browser_cache_file)
cache_file_popup_url = os.path.join(cache_root, config_ghostwriter.url_file)

page_url = []

with open(Path(__file__).resolve().parent / 'css/main.css', 'r') as f:
    css = f.read()
with open(Path(__file__).resolve().parent / 'js/main.js', 'r') as f:
    js = f.read()


def add_text(history, text):
    history = history + [(text, None)]
    return history, gr.update(value='', interactive=False)


def rm_text(history):
    history = history[:-1] + [(history[-1][0], None)]
    return history, gr.update(value='', interactive=False)


def add_text_shortcut(history, text):
    key_word = {
        'summarize': '总结以上内容',
        'idea': '请根据以上内容，提出三个有新意的观点',
        'title': '请给以上内容取一个吸睛的标题'
    }
    history = history + [(key_word[text], None)]
    return history, gr.update(value='', interactive=False)


def add_file(history, file):
    history = history + [((file.name, ), None)]
    return history


def set_page_url():
    lines = []
    assert os.path.exists(cache_file_popup_url)
    for line in jsonlines.open(cache_file_popup_url):
        lines.append(line)
    page_url.append(lines[-1]['url'])
    print('now page url is: ', page_url[-1])


def bot(history):
    if not os.path.exists(cache_file):
        gr.Info("Please add this page to Qwen's Reading List first!")
        yield history

    now_page = None
    for line in jsonlines.open(cache_file):
        if line['url'] == page_url[-1]:
            now_page = line
            break

    if not now_page:
        gr.Info("This page has not yet been added to the Qwen's reading list!")

    _ref_list = mem.get(history[-1][0], [now_page], llm=llm, stream=False, max_token=config_ghostwriter.MAX_TOKEN)
    if _ref_list:
        _ref = '\n'.join(json.dumps(x, ensure_ascii=False) for x in _ref_list)
    else:
        _ref = ''
    print(_ref)
    agent = Simple(stream=True, llm=llm)
    history[-1][1] = ''
    response = agent.run(_ref, history)

    for chunk in response:
        history[-1][1] += chunk
        yield history

    # save history
    now_page['session'] = history
    lines = []
    for line in jsonlines.open(cache_file):
        if line['url'] != page_url[-1]:
            lines.append(line)

    lines.append(now_page)
    with jsonlines.open(cache_file, mode='w') as writer:
        for new_line in lines:
            writer.write(new_line)


def load_history_session(history):
    now_page = None
    if not os.path.exists(cache_file):
        gr.Info("Please add this page to Qwen's Reading List first!")
        return []
    for line in jsonlines.open(cache_file):
        if line['url'] == page_url[-1]:
            now_page = line
    if not now_page:
        gr.Info("Please add this page to Qwen's Reading List first!")
        return []
    if not now_page['raw']:
        gr.Info('Qwen is analyzing, parsing PDF takes some time...')
        return []
    return now_page['session']


def clear_session():
    now_page = None
    lines = []
    for line in jsonlines.open(cache_file):
        if line['url'] == page_url[-1]:
            now_page = line
        else:
            lines.append(line)
    now_page['session'] = []
    lines.append(now_page)
    with jsonlines.open(cache_file, mode='w') as writer:
        for new_line in lines:
            writer.write(new_line)

    return None


with gr.Blocks(css=css, theme='soft') as demo:
    chatbot = gr.Chatbot([],
                         elem_id='chatbot',
                         height=480,
                         avatar_images=(None, (os.path.join(
                             os.path.dirname(__file__), 'static/logo.png'))))
    with gr.Row():
        with gr.Column(scale=0.06, min_width=0):
            clr_bt = gr.Button('🧹')
        with gr.Column(scale=0.74):
            txt = gr.Textbox(show_label=False,
                             placeholder='Chat with Qwen...',
                             container=False)
        with gr.Column(scale=0.06, min_width=0):
            smt_bt = gr.Button('⏎')
        with gr.Column(scale=0.06, min_width=0):
            stop_bt = gr.Button('🚫')
        with gr.Column(scale=0.06, min_width=0):
            re_bt = gr.Button('🔄')

    txt_msg = txt.submit(add_text, [chatbot, txt], [chatbot, txt],
                         queue=False).then(bot, chatbot, chatbot)
    txt_msg.then(lambda: gr.update(interactive=True), None, [txt], queue=False)

    txt_msg_bt = smt_bt.click(add_text, [chatbot, txt], [chatbot, txt],
                              queue=False).then(bot, chatbot, chatbot)
    txt_msg_bt.then(lambda: gr.update(interactive=True),
                    None, [txt],
                    queue=False)

    clr_bt.click(clear_session, None, chatbot, queue=False)
    re_txt_msg = re_bt.click(rm_text, [chatbot], [chatbot, txt], queue=False).then(bot, chatbot, chatbot)
    re_txt_msg.then(lambda: gr.update(interactive=True), None, [txt], queue=False)

    stop_bt.click(None, None, None, cancels=[txt_msg, txt_msg_bt, re_txt_msg], queue=False)

    demo.load(set_page_url).then(load_history_session, chatbot, chatbot)

demo.queue().launch(server_name=config_ghostwriter.app_in_browser_host, server_port=config_ghostwriter.app_in_browser_port)
