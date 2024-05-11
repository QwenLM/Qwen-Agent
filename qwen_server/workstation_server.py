import datetime
import json
import os
from pathlib import Path

try:
    import add_qwen_libs  # NOQA
except ImportError:
    pass
from qwen_agent.agents import ArticleAgent, Assistant, ReActChat
from qwen_agent.gui import gr
from qwen_agent.gui.utils import get_avatar_image
from qwen_agent.llm import get_chat_model
from qwen_agent.llm.base import ModelServiceError
from qwen_agent.memory import Memory
from qwen_agent.tools.simple_doc_parser import PARSER_SUPPORTED_FILE_TYPES
from qwen_agent.utils.utils import get_basename_from_url, get_file_type, has_chinese_chars, save_text_to_file
from qwen_server import output_beautify
from qwen_server.schema import GlobalConfig
from qwen_server.utils import read_meta_data_by_condition, save_browsing_meta_data

# Read config
with open(Path(__file__).resolve().parent / 'server_config.json', 'r') as f:
    server_config = json.load(f)
    server_config = GlobalConfig(**server_config)
llm_config = None

if hasattr(server_config.server, 'llm'):
    llm_config = {
        'model': server_config.server.llm,
        'api_key': server_config.server.api_key,
        'model_server': server_config.server.model_server
    }

app_global_para = {
    'time': [str(datetime.date.today()), str(datetime.date.today())],
    'messages': [],
    'last_turn_msg_id': [],
    'is_first_upload': True,
    'uploaded_ci_file': '',
    'pure_messages': [],
    'pure_last_turn_msg_id': [],
}

DOC_OPTION = 'Document QA'
CI_OPTION = 'Code Interpreter'
CODE_FLAG = '/code'
PLUGIN_FLAG = '/plug'
TITLE_FLAG = '/title'

with open(Path(__file__).resolve().parent / 'css/main.css', 'r') as f:
    css = f.read()
with open(Path(__file__).resolve().parent / 'js/main.js', 'r') as f:
    js = f.read()

meta_file = os.path.join(server_config.path.work_space_root, 'meta_data.jsonl')


def add_text(history, text):
    history = history + [(text, None)]
    app_global_para['last_turn_msg_id'] = []
    return history, gr.update(value='', interactive=False)


def pure_add_text(history, text):
    history = history + [(text, None)]
    app_global_para['pure_last_turn_msg_id'] = []
    return history, gr.update(value='', interactive=False)


def rm_text(history):
    if not history:
        gr.Warning('No input content!')
    elif not history[-1][1]:
        return history, gr.update(value='', interactive=False)
    else:
        history = history[:-1] + [(history[-1][0], None)]
        return history, gr.update(value='', interactive=False)


def chat_clear():
    app_global_para['messages'] = []
    return None, None


def chat_clear_pure():
    app_global_para['pure_messages'] = []
    return None, None


def chat_clear_last():
    for index in app_global_para['last_turn_msg_id'][::-1]:
        del app_global_para['messages'][index]
    app_global_para['last_turn_msg_id'] = []


def pure_chat_clear_last():
    for index in app_global_para['pure_last_turn_msg_id'][::-1]:
        del app_global_para['pure_messages'][index]
    app_global_para['pure_last_turn_msg_id'] = []


def add_file(file, chosen_plug):
    display_path = get_basename_from_url(file.name)

    if chosen_plug == CI_OPTION:
        app_global_para['uploaded_ci_file'] = file.name
        app_global_para['is_first_upload'] = True
        return display_path
    f_type = get_file_type(file)
    if f_type not in PARSER_SUPPORTED_FILE_TYPES:
        display_path = (
            f'Upload failed: only adding {", ".join(PARSER_SUPPORTED_FILE_TYPES)} as references is supported!')
    else:
        # cache file
        try:
            mem = Memory()
            *_, last = mem.run([{'role': 'user', 'content': [{'file': file.name}]}])
            title = display_path
            save_browsing_meta_data(file.name, title, meta_file)

        except Exception as ex:
            raise ValueError(ex)

    return display_path


def update_app_global_para(date1, date2):
    app_global_para['time'][0] = date1
    app_global_para['time'][1] = date2


def refresh_date():
    option = [str(datetime.date.today() - datetime.timedelta(days=i)) for i in range(server_config.server.max_days)]
    return (gr.update(choices=option,
                      value=str(datetime.date.today())), gr.update(choices=option, value=str(datetime.date.today())))


def update_browser_list():
    br_list = read_meta_data_by_condition(meta_file, time_limit=app_global_para['time'])
    if not br_list:
        return 'No browsing records'

    br_list = [[line['url'], line['title'], line['checked']] for line in br_list]

    res = '<ol>{bl}</ol>'
    bl = ''
    for i, x in enumerate(br_list):
        ck = '<input type="checkbox" class="custom-checkbox" id="ck-' + x[0] + '" '
        if x[2]:
            ck += 'checked>'
        else:
            ck += '>'
        bl += '<li>{checkbox}{title}<a href="{url}"> [url]</a></li>'.format(checkbox=ck, url=x[0], title=x[1])
    res = res.format(bl=bl)
    return res


def layout_to_right(text):
    return text, text


def download_text(text):
    now = datetime.datetime.now()
    current_time = now.strftime('%Y-%m-%d_%H-%M-%S')
    filename = f'file_{current_time}.md'
    save_path = os.path.join(server_config.path.download_root, filename)
    try:
        save_text_to_file(save_path, text)
        gr.Info(f'Saved to {save_path}')
    except Exception as ex:
        gr.Error(f'Failed to save this file.\n {str(ex)}')


def choose_plugin(chosen_plugin):
    if chosen_plugin == CI_OPTION:
        gr.Info('Code execution is NOT sandboxed. Do NOT ask Qwen to perform dangerous tasks.')
    if chosen_plugin == CI_OPTION or chosen_plugin == DOC_OPTION:
        return gr.update(interactive=True), None
    else:
        return gr.update(interactive=False), None


def pure_bot(history):
    if not history:
        yield history
    else:
        history[-1][1] = ''
        message = [{'role': 'user', 'content': history[-1][0], 'name': 'pure_chat_user'}]
        try:
            llm = get_chat_model(llm_config)
            response = llm.chat(messages=app_global_para['pure_messages'] + message)
            rsp = []
            for rsp in response:
                if rsp:
                    history[-1][1] = rsp[-1]['content']
                    yield history

            # Record the conversation history when the conversation succeeds
            app_global_para['pure_last_turn_msg_id'].append(len(app_global_para['pure_messages']))
            app_global_para['pure_messages'].extend(message)  # New user message
            app_global_para['pure_last_turn_msg_id'].append(len(app_global_para['pure_messages']))
            app_global_para['pure_messages'].extend(rsp)  # The response

        except ModelServiceError as ex:
            history[-1][1] = str(ex)
            yield history
        except Exception as ex:
            raise ValueError(ex)


def keep_only_files_for_name(messages, name):
    new_messages = []
    for message in messages:
        if message['role'] == 'user' and ('name' not in message or message['name'] != name):
            # rm files
            if isinstance(message['content'], list):
                new_content = []
                for item in message['content']:
                    for k, v in item.items():
                        if k != 'file':  # rm files
                            new_content.append(item)
                new_messages.append({'role': message['role'], 'content': new_content})
            else:
                new_messages.append(message)
        else:
            new_messages.append(message)
    return new_messages


def bot(history, chosen_plug):
    if not history:
        yield history
    else:
        history[-1][1] = ''
        if chosen_plug == CI_OPTION:  # use code interpreter
            if app_global_para['uploaded_ci_file'] and app_global_para['is_first_upload']:
                app_global_para['is_first_upload'] = False  # only send file when first upload
                message = [{
                    'role': 'user',
                    'content': [{
                        'text': history[-1][0]
                    }, {
                        'file': app_global_para['uploaded_ci_file']
                    }],
                    'name': 'ci'
                }]
            else:
                message = [{'role': 'user', 'content': history[-1][0], 'name': 'ci'}]
            messages = keep_only_files_for_name(app_global_para['messages'], 'ci') + message
            func_assistant = ReActChat(function_list=['code_interpreter'], llm=llm_config)
            try:
                response = func_assistant.run(messages=messages)
                rsp = []
                for rsp in response:
                    if rsp:
                        history[-1][1] = rsp[-1]['content']
                        yield history
                # append message
                app_global_para['last_turn_msg_id'].append(len(app_global_para['messages']))
                app_global_para['messages'].extend(message)
                app_global_para['last_turn_msg_id'].append(len(app_global_para['messages']))
                app_global_para['messages'].extend(rsp)
            except ModelServiceError as ex:
                history[-1][1] = str(ex)
                yield history
            except Exception as ex:
                raise ValueError(ex)
        else:
            try:
                content = [{'text': history[-1][0]}]
                # checked files
                for record in read_meta_data_by_condition(meta_file, time_limit=app_global_para['time'], checked=True):
                    content.append({'file': record['url']})
                qa_assistant = Assistant(llm=llm_config)
                message = [{'role': 'user', 'content': content}]
                # rm all files of history
                messages = keep_only_files_for_name(app_global_para['messages'], 'None') + message
                response = qa_assistant.run(messages=messages, max_ref_token=server_config.server.max_ref_token)
                rsp = []
                for rsp in response:
                    if rsp:
                        history[-1][1] = rsp[-1]['content']
                        yield history
                # append message
                app_global_para['last_turn_msg_id'].append(len(app_global_para['messages']))
                app_global_para['messages'].extend(message)
                app_global_para['last_turn_msg_id'].append(len(app_global_para['messages']))
                app_global_para['messages'].extend(rsp)

            except ModelServiceError as ex:
                history[-1][1] = str(ex)
                yield history
            except Exception as ex:
                raise ValueError(ex)


def get_last_one_line_context(text):
    lines = text.split('\n')
    n = len(lines)
    res = ''
    for i in range(n - 1, -1, -1):
        if lines[i].strip():
            res = lines[i]
            break
    return res


def generate(context):
    sp_query = get_last_one_line_context(context)
    if CODE_FLAG in sp_query:  # router to code interpreter
        sp_query = sp_query.split(CODE_FLAG)[-1]
        if has_chinese_chars(sp_query):
            sp_query += ', 必须使用code_interpreter工具'
        else:
            sp_query += ' (Please use code_interpreter.)'

        func_assistant = ReActChat(function_list=['code_interpreter'], llm=llm_config)
        try:
            response = func_assistant.run(messages=[{'role': 'user', 'content': sp_query}])
            for rsp in response:
                if rsp:
                    yield rsp[-1]['content']
        except ModelServiceError as ex:
            yield str(ex)
        except Exception as ex:
            raise ValueError(ex)

    elif PLUGIN_FLAG in sp_query:  # router to plugin
        sp_query = sp_query.split(PLUGIN_FLAG)[-1]
        func_assistant = ReActChat(function_list=['code_interpreter', 'image_gen'], llm=llm_config)
        try:
            response = func_assistant.run(messages=[{'role': 'user', 'content': sp_query}])
            for rsp in response:
                if rsp:
                    yield rsp[-1]['content']
        except ModelServiceError as ex:
            yield str(ex)
        except Exception as ex:
            raise ValueError(ex)

    else:  # router to continue writing
        sp_query_no_title = context
        if TITLE_FLAG in sp_query:  # /title
            sp_query_no_title = sp_query.split(TITLE_FLAG)[-1]

        full_article = False
        if TITLE_FLAG in sp_query:  # /title
            full_article = True
        try:
            writing_assistant = ArticleAgent(llm=llm_config)

            content = [{'text': sp_query_no_title}]
            # checked files
            for record in read_meta_data_by_condition(meta_file, time_limit=app_global_para['time'], checked=True):
                content.append({'file': record['url']})

            response = writing_assistant.run(messages=[{
                'role': 'user',
                'content': content
            }],
                                             max_ref_token=server_config.server.max_ref_token,
                                             full_article=full_article)
            for rsp in response:
                if rsp:
                    yield '\n'.join([x['content'] for x in rsp])
        except ModelServiceError as ex:
            yield str(ex)
        except Exception as ex:
            raise ValueError(ex)


def format_generate(edit, context):
    res = edit
    yield res
    if '> Writing Text:' in context:
        text = context.split('> Writing Text:')[-1].strip()
        res += '\n'
        res += text
        yield res
    elif 'Answer:' in context:
        response = output_beautify.format_answer(context)
        res += '\n'
        res += response
        yield res
    else:
        res += context
        yield res


with gr.Blocks(css=css, js=js, theme='soft') as demo:
    title = gr.Markdown('Qwen Agent: BrowserQwen', elem_classes='title')
    desc = gr.Markdown(
        'This is the editing workstation of BrowserQwen, where Qwen has collected the browsing history. Qwen can assist you in completing your creative work!',
        elem_classes='desc',
    )

    with gr.Row():
        with gr.Column():
            rec = gr.Markdown('Browsing History', elem_classes='rec')
            with gr.Row():
                with gr.Column(scale=3, min_width=0):
                    date1 = gr.Dropdown(
                        [
                            str(datetime.date.today() - datetime.timedelta(days=i))
                            for i in range(server_config.server.max_days)
                        ],
                        value=str(datetime.date.today()),
                        label='Start Date',
                    )
                    date2 = gr.Dropdown(
                        [
                            str(datetime.date.today() - datetime.timedelta(days=i))
                            for i in range(server_config.server.max_days)
                        ],
                        value=str(datetime.date.today()),
                        label='End Date',
                    )
                with gr.Column(scale=7, min_width=0):
                    browser_list = gr.HTML(
                        value='',
                        label='browser_list',
                        elem_classes=['div_tmp', 'add_scrollbar'],
                    )

    with gr.Tab('Editor', elem_id='default-tab'):
        with gr.Row():
            with gr.Column():
                with gr.Row():
                    edit_area = gr.Textbox(
                        value='',
                        elem_classes=['textbox_default', 'add_scrollbar'],
                        lines=30,
                        label='Input',
                        show_copy_button=True,
                    )
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
                cmd_area = gr.Textbox(lines=10, max_lines=10, label="Qwen's Inner Thought", elem_id='cmd')
                with gr.Tab('Markdown'):
                    # md_out_bt = gr.Button('Render')
                    md_out_area = gr.Markdown(elem_classes=['md_tmp', 'add_scrollbar'])

                with gr.Tab('HTML'):
                    html_out_area = gr.HTML()

                with gr.Tab('Raw'):
                    text_out_area = gr.Textbox(
                        lines=20,
                        label='',
                        elem_classes=['textbox_default_output', 'add_scrollbar'],
                        show_copy_button=True,
                    )
        clk_ctn_bt = ctn_bt.click(generate, edit_area, cmd_area)
        clk_ctn_bt.then(format_generate, [edit_area, cmd_area], edit_area)

        edit_area_change = edit_area.change(layout_to_right, edit_area, [text_out_area, md_out_area])

        stop_bt.click(lambda: None, cancels=[clk_ctn_bt], queue=False)
        clr_bt.click(
            lambda: [None, None, None],
            None,
            [edit_area, cmd_area, md_out_area],
            queue=False,
        )
        dld_bt.click(download_text, edit_area, None)

        # layout_bt.click(layout_to_right,
        #                 edit_area, [text_out_area, md_out_area],
        #                 queue=False)
        gr.Markdown("""
    ### Usage Tips:
    - Browsing History:
        - Start Date/End Date: Selecting the browsed materials for the desired time period, including the start and end dates
        - The browsed materials list: supporting the selection or removal of specific browsing content
    - Editor: In the editing area, you can directly input content or special instructions, and then click the ```Continue``` button to have Qwen assist in completing the editing work:
        - After inputting the content, directly click the ```Continue``` button: Qwen will begin to continue writing based on the browsing information
        - Using special instructions:
            - /title + content: Qwen enables the built-in planning process and writes a complete manuscript
            - /code + content: Qwen enables the code interpreter plugin, writes and runs Python code, and generates replies
            - /plug + content: Qwen enables plugin and select appropriate plugin to generate reply
    - Chat: Interactive area. Qwen generates replies based on given reference materials. Selecting Code Interpreter will enable the code interpreter plugin

        """)

    with gr.Tab('Chat', elem_id='chat-tab'):
        with gr.Column():
            chatbot = gr.Chatbot(
                [],
                elem_id='chatbot',
                height=680,
                show_copy_button=True,
                avatar_images=(None, get_avatar_image('qwen')),
            )
            with gr.Row():
                with gr.Column(scale=1, min_width=0):
                    file_btn = gr.UploadButton('Upload', file_types=['file'])

                with gr.Column(scale=13):
                    chat_txt = gr.Textbox(
                        show_label=False,
                        placeholder='Chat with Qwen...',
                        container=False,
                    )
                with gr.Column(scale=1, min_width=0):
                    chat_clr_bt = gr.Button('Clear')

                with gr.Column(scale=1, min_width=0):
                    chat_stop_bt = gr.Button('Stop')
                with gr.Column(scale=1, min_width=0):
                    chat_re_bt = gr.Button('Again')
            with gr.Row():
                with gr.Column(scale=2, min_width=0):
                    plug_bt = gr.Dropdown(
                        [CI_OPTION, DOC_OPTION],
                        label='Plugin',
                        info='',
                        value=DOC_OPTION,
                    )
                with gr.Column(scale=8, min_width=0):
                    hidden_file_path = gr.Textbox(interactive=False, label='The uploaded file is displayed here')

            txt_msg = chat_txt.submit(add_text, [chatbot, chat_txt], [chatbot, chat_txt],
                                      queue=False).then(bot, [chatbot, plug_bt], chatbot)
            txt_msg.then(lambda: gr.update(interactive=True), None, [chat_txt], queue=False)

            re_txt_msg = (chat_re_bt.click(rm_text, [chatbot], [chatbot, chat_txt],
                                           queue=False).then(chat_clear_last, None,
                                                             None).then(bot, [chatbot, plug_bt], chatbot))
            re_txt_msg.then(lambda: gr.update(interactive=True), None, [chat_txt], queue=False)

            file_msg = file_btn.upload(add_file, [file_btn, plug_bt], [hidden_file_path], queue=False)
            file_msg.then(update_browser_list, None, browser_list)

            chat_clr_bt.click(chat_clear, None, [chatbot, hidden_file_path], queue=False)
            # re_bt.click(re_bot, chatbot, chatbot)
            chat_stop_bt.click(chat_clear_last, None, None, cancels=[txt_msg, re_txt_msg], queue=False)

            plug_bt.change(choose_plugin, plug_bt, [file_btn, hidden_file_path])

    with gr.Tab('Pure Chat', elem_id='pure-chat-tab'):
        gr.Markdown('Note: The chat box on this tab will not use any browsing history!')
        with gr.Column():
            pure_chatbot = gr.Chatbot(
                [],
                elem_id='pure_chatbot',
                height=680,
                show_copy_button=True,
                avatar_images=(None, get_avatar_image('qwen')),
            )
            with gr.Row():
                with gr.Column(scale=13):
                    chat_txt = gr.Textbox(
                        show_label=False,
                        placeholder='Chat with Qwen...',
                        container=False,
                    )
                with gr.Column(scale=1, min_width=0):
                    chat_clr_bt = gr.Button('Clear')
                with gr.Column(scale=1, min_width=0):
                    chat_stop_bt = gr.Button('Stop')
                with gr.Column(scale=1, min_width=0):
                    chat_re_bt = gr.Button('Again')

            txt_msg = chat_txt.submit(pure_add_text, [pure_chatbot, chat_txt], [pure_chatbot, chat_txt],
                                      queue=False).then(pure_bot, pure_chatbot, pure_chatbot)
            txt_msg.then(lambda: gr.update(interactive=True), None, [chat_txt], queue=False)

            re_txt_msg = chat_re_bt.click(rm_text, [pure_chatbot], [pure_chatbot, chat_txt],
                                          queue=False).then(pure_chat_clear_last, None,
                                                            None).then(pure_bot, pure_chatbot, pure_chatbot)
            re_txt_msg.then(lambda: gr.update(interactive=True), None, [chat_txt], queue=False)

            chat_clr_bt.click(chat_clear_pure, None, pure_chatbot, queue=False)

            chat_stop_bt.click(pure_chat_clear_last, None, None, cancels=[txt_msg, re_txt_msg], queue=False)

    date1.change(update_app_global_para, [date1, date2],
                 None).then(update_browser_list, None, browser_list).then(chat_clear, None, [chatbot, hidden_file_path])
    date2.change(update_app_global_para, [date1, date2],
                 None).then(update_browser_list, None, browser_list).then(chat_clear, None, [chatbot, hidden_file_path])

    demo.load(update_app_global_para, [date1, date2],
              None).then(refresh_date, None,
                         [date1, date2]).then(update_browser_list, None,
                                              browser_list).then(chat_clear, None, [chatbot, hidden_file_path])

demo.queue().launch(server_name=server_config.server.server_host, server_port=server_config.server.workstation_port)
