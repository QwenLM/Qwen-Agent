import importlib
import json
import os
import sys
from pathlib import Path

import gradio as gr
import jsonlines

import config_browserqwen

sys.path.insert(
    0,
    str(Path(__file__).absolute().parent.parent))  # NOQA

from qwen_agent.actions import Simple  # NOQA
from qwen_agent.memory import Memory  # NOQA

prompt_lan = sys.argv[1]
llm_name = sys.argv[2]
max_ref_token = int(sys.argv[3])
model_server = sys.argv[4]
api_key = sys.argv[5]
server_host = sys.argv[6]

if llm_name.startswith('gpt'):
    module = 'qwen_agent.llm.gpt'
    llm = importlib.import_module(module).GPT(llm_name)
elif llm_name.startswith('Qwen') or llm_name.startswith('qwen'):
    module = 'qwen_agent.llm.qwen'
    llm = importlib.import_module(module).Qwen(llm_name, model_server=model_server, api_key=api_key)
else:
    raise NotImplementedError

mem = Memory(config_browserqwen.similarity_search, config_browserqwen.similarity_search_type)

cache_file = os.path.join(config_browserqwen.cache_root, config_browserqwen.browser_cache_file)
cache_file_popup_url = os.path.join(config_browserqwen.cache_root, config_browserqwen.url_file)

page_url = []

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
    if not history:
        yield history
    else:
        now_page = None
        _ref = ''
        if not os.path.exists(cache_file):
            gr.Info("Please add this page to Qwen's Reading List first!")
        else:
            for line in jsonlines.open(cache_file):
                if line['url'] == page_url[-1]:
                    now_page = line

            if not now_page:
                gr.Info("This page has not yet been added to the Qwen's reading list!")
            elif not now_page['raw']:
                gr.Info('Please wait, Qwen is analyzing this page...')
            else:
                _ref_list = mem.get(history[-1][0], [now_page], llm=llm, stream=False, max_token=max_ref_token)
                if _ref_list:
                    _ref = '\n'.join(json.dumps(x, ensure_ascii=False) for x in _ref_list)
                else:
                    _ref = ''
        # print(_ref)
        agent = Simple(stream=True, llm=llm)
        history[-1][1] = ''
        response = agent.run(_ref, history, prompt_lan=prompt_lan)

        for chunk in response:
            history[-1][1] += chunk
            yield history

        # save history
        if now_page:
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
        gr.Info('Please wait, Qwen is analyzing this page...')
        return []
    return now_page['session']


def clear_session():
    if not os.path.exists(cache_file):
        return None
    now_page = None
    lines = []
    for line in jsonlines.open(cache_file):
        if line['url'] == page_url[-1]:
            now_page = line
        else:
            lines.append(line)
    if not now_page:
        return None
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
                             Path(__file__).resolve().parent, 'img/logo.png'))))
    with gr.Row():
        with gr.Column(scale=0.7):
            txt = gr.Textbox(show_label=False,
                             placeholder='Chat with Qwen...',
                             container=False)
        # with gr.Column(scale=0.06, min_width=0):
        #     smt_bt = gr.Button('⏎')
        with gr.Column(scale=0.1, min_width=0):
            clr_bt = gr.Button('🧹', elem_classes='bt_small_font')
        with gr.Column(scale=0.1, min_width=0):
            stop_bt = gr.Button('🚫', elem_classes='bt_small_font')
        with gr.Column(scale=0.1, min_width=0):
            re_bt = gr.Button('🔁', elem_classes='bt_small_font')

    txt_msg = txt.submit(add_text, [chatbot, txt], [chatbot, txt],
                         queue=False).then(bot, chatbot, chatbot)
    txt_msg.then(lambda: gr.update(interactive=True), None, [txt], queue=False)

    # txt_msg_bt = smt_bt.click(add_text, [chatbot, txt], [chatbot, txt],
    #                           queue=False).then(bot, chatbot, chatbot)
    # txt_msg_bt.then(lambda: gr.update(interactive=True),
    #                 None, [txt],
    #                 queue=False)

    clr_bt.click(clear_session, None, chatbot, queue=False)
    re_txt_msg = re_bt.click(rm_text, [chatbot], [chatbot, txt], queue=False).then(bot, chatbot, chatbot)
    re_txt_msg.then(lambda: gr.update(interactive=True), None, [txt], queue=False)

    stop_bt.click(None, None, None, cancels=[txt_msg, re_txt_msg], queue=False)

    demo.load(set_page_url).then(load_history_session, chatbot, chatbot)

demo.queue().launch(server_name=server_host, server_port=config_browserqwen.app_in_browser_port)
