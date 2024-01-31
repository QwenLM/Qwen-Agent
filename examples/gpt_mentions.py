import gradio as gr

from qwen_agent.agents import Assistant, DocQAAgent, ReActChat
from qwen_agent.llm.base import ModelServiceError
from qwen_server import output_beautify


def run_adapter(messages):
    llm_cfg = {
        # Use the model service provided by DashScope:
        'model': 'qwen-max',
        'model_server': 'dashscope',
        # Use your own model service compatible with OpenAI API:
        # 'model': 'Qwen',
        # 'model_server': 'http://127.0.0.1:7905/v1',

        # (Optional) LLM hyper-paramters:
        'generate_cfg': {
            'top_p': 0.8
        }
    }

    agent_list = {
        'code_interpreter': {
            'object': ReActChat,
            'params': {
                'system_message':
                'you are a programming expert, skilled in writing code to solve mathematical problems and data analysis problems.',
                'function_list': ['code_interpreter'],
                'llm': llm_cfg
            }
        },
        'doc_qa': {
            'object': DocQAAgent,
            'params': {
                'llm': llm_cfg
            }
        },
        'assistant': {
            'object': Assistant,
            'params': {
                'llm': llm_cfg
            }
        }
    }

    selected_agent_name = messages[-1]['content'][0]['text'].split(
        '@')[-1].strip()
    selected_agent = agent_list[selected_agent_name]['object'](
        **agent_list[selected_agent_name]['params'])

    try:
        for rsp in selected_agent.run(messages=messages):
            yield rsp
    except ModelServiceError:
        yield [{
            'role': 'assistant',
            'content': '模型调用出错，可能的原因有：未正确配置模型参数，或输入数据不安全等'
        }]
    except Exception as ex:
        raise ValueError(ex)


# =========================================================
# Below is the gradio service: front-end and back-end logic
# =========================================================

app_global_para = {
    'messages': [],
    'is_first_upload': True,
    'uploaded_file': ''
}

AGENT_LIST_NAME = ['code_interpreter', 'doc_qa', 'assistant']


def add_text(history, text):
    history = history + [(text, None)]
    return history, gr.update(value='', interactive=False)


def chat_clear():
    app_global_para['messages'] = []
    return None, None


def add_file(file):
    app_global_para['uploaded_file'] = file.name
    app_global_para['is_first_upload'] = True
    return file.name


def bot(history, chosen_plug):
    if not history:
        yield history
    else:
        if '@' not in history[-1][0]:
            history[-1][0] += ('@' + chosen_plug)

        content = [{'text': history[-1][0]}]
        if app_global_para['uploaded_file'] and app_global_para[
                'is_first_upload']:
            app_global_para[
                'is_first_upload'] = False  # only send file when first upload
            content.append({'file': app_global_para['uploaded_file']})
        app_global_para['messages'].append({
            'role': 'user',
            'content': content
        })

        history[-1][1] = ''
        response = []
        for response in run_adapter(messages=app_global_para['messages']):
            if response:
                display_response = output_beautify.convert_fncall_to_text(
                    response)
                history[-1][1] = display_response[-1]['content']
                yield history

        # append message
        app_global_para['messages'].extend(response)


with gr.Blocks(theme='soft') as demo:
    with gr.Tab('Chat', elem_id='chat-tab'):
        with gr.Column():
            chatbot = gr.Chatbot(
                [],
                elem_id='chatbot',
                height=1500,
                show_copy_button=True,
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

            with gr.Row():
                with gr.Column(scale=2, min_width=0):
                    plug_bt = gr.Dropdown(
                        AGENT_LIST_NAME,
                        label='Mention List',
                        info='',
                        value='assistant',
                    )
                with gr.Column(scale=8, min_width=0):
                    hidden_file_path = gr.Textbox(
                        interactive=False,
                        label='The uploaded file is displayed here')

            txt_msg = chat_txt.submit(add_text, [chatbot, chat_txt],
                                      [chatbot, chat_txt],
                                      queue=False).then(
                                          bot, [chatbot, plug_bt], chatbot)
            txt_msg.then(lambda: gr.update(interactive=True),
                         None, [chat_txt],
                         queue=False)

            file_msg = file_btn.upload(add_file,
                                       file_btn, [hidden_file_path],
                                       queue=False)

            chat_clr_bt.click(chat_clear,
                              None, [chatbot, hidden_file_path],
                              queue=False)

demo.queue().launch()
