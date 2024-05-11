"""A gpt @mentions gradio demo"""

from qwen_agent.agents import Assistant, ReActChat
from qwen_agent.agents.doc_qa import BasicDocQA
from qwen_agent.gui import WebUI


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


def app_gui():
    agent_list = init_agent_service()
    chatbotConfig = {
        'prompt.suggestions': [
            '@代码解释器 2 ^ 10 = ?',
            '@文档问答 这篇论文解决了什么问题？',
            '@小助理 你好！',
        ],
        'verbose': True
    }
    WebUI(
        agent_list,
        chatbot_config=chatbotConfig,
    ).run(messages=[{
        'role': 'assistant',
        'content': [{
            'text': '试试看 @代码解释器 来问我~'
        }]
    }])


if __name__ == '__main__':
    app_gui()
