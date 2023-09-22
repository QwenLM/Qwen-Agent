import datetime
import importlib
import json
import os
import random
import sys
from pathlib import Path

import gradio as gr
import jsonlines

sys.path.insert(
    0,
    str(Path(__file__).absolute().parent.parent.parent))  # NOQA

from qwen_agent.agents.actions.plugin import Plugin, format_answer  # NOQA
from qwen_agent.agents.tools.tools import tools_list  # NOQA
from qwen_agent.utils.util import get_last_one_line_context, save_text_to_file, count_tokens, get_html_content  # NOQA
from qwen_agent.agents.actions import ContinueWriting, Simple, WriteFromZero  # NOQA
from qwen_agent.configs import config_browserqwen  # NOQA
from qwen_agent.agents.memory import Memory  # NOQA

if not os.path.exists(config_browserqwen.cache_root):
    os.makedirs(config_browserqwen.cache_root)
if not os.path.exists(config_browserqwen.download_root):
    os.makedirs(config_browserqwen.download_root)
if not os.path.exists(config_browserqwen.code_interpreter_ws):
    os.makedirs(config_browserqwen.code_interpreter_ws)

if config_browserqwen.llm.startswith('gpt'):
    module = 'qwen_agent.llm.gpt'
    llm = importlib.import_module(module).GPT(config_browserqwen.llm)
elif config_browserqwen.llm.startswith('Qwen'):
    module = 'qwen_agent.llm.qwen'
    llm = importlib.import_module(module).Qwen(config_browserqwen.llm)
else:
    llm = None

mem = Memory(config_browserqwen.similarity_search, config_browserqwen.similarity_search_type)

app_global_para = {
    'time': [str(datetime.date.today()), str(datetime.date.today())],
    'cache_file': os.path.join(config_browserqwen.cache_root, config_browserqwen.browser_cache_file),
    'use_ci_flag': False
}

with open(Path(__file__).resolve().parent.parent / 'css/main.css', 'r') as f:
    css = f.read()
with open(Path(__file__).resolve().parent.parent / 'js/main.js', 'r') as f:
    js = f.read()


def add_text(history, text):
    history = history + [(text, None)]
    return history, gr.update(value='', interactive=False)


def rm_text(history):
    history = history[:-1] + [(history[-1][0], None)]
    return history, gr.update(value='', interactive=False)


def add_file(history, file):
    history = history + [((file.name, ), None)]
    return history


def read_records(file, times=None):
    lines = []
    if times:
        for line in jsonlines.open(file):
            if times[0] <= line['time'] <= times[1]:
                lines.append(line)
    return lines


def update_rec_list(flag):
    # 更新推荐列表
    rec_list = []
    if not os.path.exists(app_global_para['cache_file']):
        return 'No browsing records'
    lines = []
    for line in jsonlines.open(app_global_para['cache_file']):
        if (app_global_para['time'][0] <= line['time'] <= app_global_para['time'][1]) and line['checked']:
            if flag == 'load' and line['topic']:
                rec_list.append(line['topic'])
            else:
                agent = Simple(llm=llm, stream=False)
                page_number = len(line['raw'])
                index = random.randint(0, page_number-1)
                if config_browserqwen.prompt_lan == 'CN':
                    topicprompt = '请提出一个有新意的吸引人的话题'
                elif config_browserqwen.prompt_lan == 'EN':
                    topicprompt = 'Please propose a new and attractive topic'
                rec = agent.run(line['raw'][index]['page_content'], topicprompt, prompt_lan=config_browserqwen.prompt_lan)
                assert isinstance(rec, str)
                rec_list.append(rec)
                line['topic'] = rec

        lines.append(line)
    if lines:
        # update cache file
        with jsonlines.open(app_global_para['cache_file'], mode='w') as writer:
            for new_line in lines:
                writer.write(new_line)

    res = '<ol>{rec}</ol>'
    rec = ''
    for x in rec_list:
        rec += '<li>{rec_topic}</li>'.format(rec_topic=x)
    res = res.format(rec=rec)
    return res


def update_app_global_para(date1, date2):
    # 更新全局变量
    app_global_para['time'][0] = date1
    app_global_para['time'][1] = date2
    app_global_para['use_ci_flag'] = False


def update_browser_list():
    if not os.path.exists(app_global_para['cache_file']):
        return 'No browsing records'
    lines = read_records(app_global_para['cache_file'], times=app_global_para['time'])

    br_list = [[line['url'], line['extract'], line['checked']] for line in lines]
    print('browser_list: ', len(br_list))
    res = '<ol>{bl}</ol>'
    bl = ''
    for i, x in enumerate(br_list):
        ck = '<input type="checkbox" class="custom-checkbox" id="ck-'+x[0]+'" '
        if x[2]:
            ck += 'checked>'
        else:
            ck += '>'
        bl += '<li>{checkbox}{title}<a href="{url}"> [url]</a></li>'.format(checkbox=ck, url=x[0], title=x[1])
    res = res.format(bl=bl)
    return res


def update_all(date1, date2):
    update_app_global_para(date1, date2)
    return update_browser_list(), update_rec_list('update')


def layout_to_right(text):
    return text, text


def download_text(text):
    now = datetime.datetime.now()
    current_time = now.strftime('%Y-%m-%d_%H-%M-%S')
    filename = f'file_{current_time}.md'
    rsp = save_text_to_file(os.path.join(config_browserqwen.download_root, filename), text)
    if rsp == 'SUCCESS':
        raise gr.Info('Saved')
    else:
        raise gr.Error("Can't Save: ", rsp)


def count_token(text):
    return count_tokens(text)


def change_use_ci_flag():
    if app_global_para['use_ci_flag']:
        app_global_para['use_ci_flag'] = False
    else:
        app_global_para['use_ci_flag'] = True


def add_url_manu(url, date):
    text = get_html_content(url)
    msg = {'content': text, 'query': '', 'url': url, 'task': 'cache', 'type': 'html'}

    from main import cache_data  # NOQA
    cache_data(msg, app_global_para['cache_file'])


def bot(history):
    if app_global_para['use_ci_flag']:  # use code interpreter
        agent = Plugin(llm=llm, list_of_plugin_info=tools_list[:1])
        response = agent.run(history[-1][0]+', use code_interpreter', history=[])
    else:
        lines = []
        for line in jsonlines.open(app_global_para['cache_file']):
            if (app_global_para['time'][0] <= line['time'] <= app_global_para['time'][1]) and line['checked']:
                lines.append(line)
        if lines:
            _ref_list = mem.get(history[-1][0], lines, llm=llm, stream=True, max_token=config_browserqwen.MAX_TOKEN)
            _ref = '\n'.join(json.dumps(x, ensure_ascii=False) for x in _ref_list)
        else:
            _ref = ''
            gr.Warning('No reference materials selected, Qwen will answer directly')

        agent = Simple(llm=llm, stream=True)
        response = agent.run(_ref, history)
    history[-1][1] = ''
    for chunk in response:
        history[-1][1] += chunk
        yield history


def generate(context):
    sp_query = get_last_one_line_context(context)

    if config_browserqwen.code_flag in sp_query:  # router to code interpreter
        sp_query = sp_query.split(config_browserqwen.code_flag)[-1]
        history = []
        agent = Plugin(llm=llm, list_of_plugin_info=tools_list[:1])
        response = agent.run(sp_query+', 必须使用code_interpreter工具', history=history)
        yield response
    elif config_browserqwen.plugin_flag in sp_query:  # router to plugin
        sp_query = sp_query.split(config_browserqwen.plugin_flag)[-1]
        history = []
        agent = Plugin(llm=llm, list_of_plugin_info=tools_list)
        response = agent.run(sp_query, history=history)
        yield response
    else:  # router to continue writing
        res = ''
        lines = []
        for line in jsonlines.open(app_global_para['cache_file']):
            if (app_global_para['time'][0] <= line['time'] <= app_global_para['time'][1]) and line['checked']:
                lines.append(line)
        if lines:
            if config_browserqwen.similarity_search:
                res += '\n========================= \n'
                yield res
                res += '> Search for relevant information: \n'
                yield res
            sp_query_no_title = sp_query
            if config_browserqwen.title_flag in sp_query:  # /title
                sp_query_no_title = sp_query.split(config_browserqwen.title_flag)[-1]

            _ref_list = mem.get(sp_query_no_title, lines, llm=llm, stream=True, max_token=config_browserqwen.MAX_TOKEN)
            _ref = '\n'.join(json.dumps(x, ensure_ascii=False) for x in _ref_list)
            res += _ref
            yield res
            res += '\n'
        else:
            _ref = ''
            gr.Warning('No reference materials selected, Qwen will answer directly')

        if config_browserqwen.title_flag in sp_query:  # /title
            sp_query = sp_query.split(config_browserqwen.title_flag)[-1]
            agent = WriteFromZero(llm=llm, stream=True, auto_agent=config_browserqwen.auto_agent)
        else:
            res += '\n========================= \n'
            res += '> Writing Text: \n'
            yield res
            agent = ContinueWriting(llm=llm, stream=True)

        response = agent.run(_ref, context, prompt_lan=config_browserqwen.prompt_lan)
        for chunk in response:
            res += chunk
            yield res
        print('OK!')


def format_generate(edit, context):
    res = edit
    yield res
    if '> Writing Text: ' in context:
        text = context.split('> Writing Text: ')[-1].strip()
        res += '\n'
        res += text
        yield res
    elif 'Final Answer' in context:
        response = format_answer(context)
        res += '\n'
        res += response
        yield res
    else:
        res += context
        yield res


with gr.Blocks(css=css, theme='soft') as demo:
    title = gr.Markdown('Qwen Agent: BrowserQwen', elem_classes='title')
    desc = gr.Markdown(
        'This is the editing workstation of BrowserQwen, where Qwen has collected the browsing history. Qwen can assist you in completing your creative work!',
        elem_classes='desc')

    with gr.Row():
        with gr.Column():
            rec = gr.Markdown('Browsing History', elem_classes='rec')
            with gr.Row():
                with gr.Column(scale=0.3, min_width=0):
                    date1 = gr.Dropdown([str(datetime.date.today()-datetime.timedelta(days=i)) for i in range(config_browserqwen.max_days)], value=str(datetime.date.today()), label='Start Date')  # NOQA
                    date2 = gr.Dropdown([str(datetime.date.today()-datetime.timedelta(days=i)) for i in range(config_browserqwen.max_days)], value=str(datetime.date.today()), label='End Date')  # NOQA
                with gr.Column(scale=0.7, min_width=0):
                    browser_list = gr.HTML(value='', label='browser_list', elem_classes=['div_tmp', 'add_scrollbar'])

    with gr.Tab('Editor', elem_id='default-tab'):
        with gr.Row():
            with gr.Column():
                with gr.Row():
                    edit_area = gr.Textbox(
                        value='',
                        elem_classes=['textbox_default', 'add_scrollbar'],
                        lines=30,
                        label='Input',
                        show_copy_button=True)
                    # token_count = gr.HTML(value='<span>0</span>',
                    #                       elem_classes=[
                    #                           'token-counter',
                    #                           'default-token-counter'
                    #                       ])

                with gr.Row():
                    ctn_bt = gr.Button('Continue', variant='primary')
                    stop_bt = gr.Button('Stop')
                    clr_bt = gr.Button('Clear')
                    dld_bt = gr.Button('Download')

                # with gr.Row():
                #     layout_bt = gr.Button('👉', variant='primary')

            with gr.Column():
                cmd_erea = gr.Textbox(lines=10, max_lines=10, label="Qwen's Inner Thought", elem_id='cmd', autoscroll=True)
                with gr.Tab('Markdown'):
                    # md_out_bt = gr.Button('Render')
                    md_out_area = gr.Markdown(elem_classes=[
                                                   'md_tmp',
                                                   'add_scrollbar'
                                               ])

                with gr.Tab('HTML'):
                    html_out_area = gr.HTML()

                with gr.Tab('Raw'):
                    text_out_area = gr.Textbox(lines=20,
                                               label='',
                                               elem_classes=[
                                                   'textbox_default_output',
                                                   'add_scrollbar'
                                               ],
                                               show_copy_button=True)
        # br_input_bt.click(add_url_manu, br_input, None).then(update_browser_list, None, browser_list).then(lambda: None, None, None, _js=f'() => {{{js}}}')
        # .then(update_rec_list, gr.Textbox('update', visible=False), rec_list)
        # clk_ctn_bt = ctn_bt.click(qwen_ctn, edit_area, edit_area)
        clk_ctn_bt = ctn_bt.click(generate, edit_area, cmd_erea)
        clk_ctn_bt.then(format_generate, [edit_area, cmd_erea], edit_area)

        edit_area_change = edit_area.change(layout_to_right, edit_area, [text_out_area, md_out_area])
        # edit_area_change.then(count_token, edit_area, token_count)

        stop_bt.click(lambda: None, cancels=[clk_ctn_bt], queue=False)
        clr_bt.click(lambda: [None, None, None], None, [edit_area, cmd_erea, md_out_area], queue=False)
        dld_bt.click(download_text, edit_area, None)

        # layout_bt.click(layout_to_right,
        #                 edit_area, [text_out_area, md_out_area],
        #                 queue=False)

    with gr.Tab('Chat', elem_id='chat-tab'):
        with gr.Column():

            chatbot = gr.Chatbot([],
                                 elem_id='chatbot',
                                 height=680,
                                 show_copy_button=True,
                                 avatar_images=(None, (os.path.join(
                                     Path(__file__).resolve().parent.parent, 'img/logo.png'))))
            with gr.Row():
                with gr.Column(scale=0.05, min_width=0):
                    chat_clr_bt = gr.Button('🧹')  # NOQA
                with gr.Column(scale=0.1, min_width=0):
                    plug_bt = gr.Checkbox(label='CI')
                with gr.Column(scale=0.74):
                    chat_txt = gr.Textbox(show_label=False, placeholder='Chat with Qwen...', container=False)  # NOQA
                with gr.Column(scale=0.05, min_width=0):
                    chat_smt_bt = gr.Button('⏎')  # NOQA
                with gr.Column(scale=0.05, min_width=0):
                    chat_stop_bt = gr.Button('🚫')  # NOQA
                with gr.Column(scale=0.05, min_width=0):
                    chat_re_bt = gr.Button('🔄')  # NOQA

                # with gr.Column(scale=0.1, min_width=0):
                #     btn = gr.UploadButton('📁', file_types=['file'])  # NOQA

            txt_msg = chat_txt.submit(add_text, [chatbot, chat_txt], [chatbot, chat_txt], queue=False).then(bot, chatbot, chatbot)
            txt_msg.then(lambda: gr.update(interactive=True), None, [chat_txt], queue=False)
            txt_msg_bt = chat_smt_bt.click(add_text, [chatbot, chat_txt], [chatbot, chat_txt], queue=False).then(bot, chatbot, chatbot)
            txt_msg_bt.then(lambda: gr.update(interactive=True), None, [chat_txt], queue=False)
            re_txt_msg = chat_re_bt.click(rm_text, [chatbot], [chatbot, chat_txt], queue=False).then(bot, chatbot, chatbot)
            re_txt_msg.then(lambda: gr.update(interactive=True), None, [chat_txt], queue=False)

            # file_msg = btn.upload(add_file, [chatbot, btn], [chatbot],
            #                       queue=False).then(bot, chatbot, chatbot)
            chat_clr_bt.click(lambda: None, None, chatbot, queue=False)
            # re_bt.click(re_bot, chatbot, chatbot)
            chat_stop_bt.click(None, None, None, cancels=[txt_msg, txt_msg_bt, re_txt_msg], queue=False)

            plug_bt.change(change_use_ci_flag)

    # img_cloud = gr.Image(height='50px')
    # update_bt.click(update_rec_list, gr.Textbox('update', visible=False), rec_list, queue=False)

    # date.change(update_all, date,  [img_cloud, browser_list, rec_list], queue=False)
    date1.change(update_app_global_para, [date1, date2], None).then(update_browser_list, None, browser_list).then(lambda: None, None, None, _js=f'() => {{{js}}}')
    date2.change(update_app_global_para, [date1, date2], None).then(update_browser_list, None, browser_list).then(lambda: None, None, None, _js=f'() => {{{js}}}')

    # demo.load(update_all, date,  [img_cloud, browser_list, rec_list])
    demo.load(update_app_global_para, [date1, date2], None).then(update_browser_list, None, browser_list).then(lambda: None, None, None, _js=f'() => {{{js}}}')
    # .then(update_rec_list, gr.Textbox('load', visible=False), rec_list, queue=False)

demo.queue().launch(server_name=config_browserqwen.app_host, server_port=config_browserqwen.app_port)
