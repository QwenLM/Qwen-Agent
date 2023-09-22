import json
import re

from qwen_agent.agents.actions.base import Action

from qwen_agent.llm.qwen import qwen_chat_no_stream  # NOQA
from qwen_agent.agents.tools.code_interpreter import code_interpreter  # NOQA
from qwen_agent.agents.tools.image_gen import image_gen  # NOQA
from qwen_agent.agents.tools.google_search import google_search  # NOQA
from qwen_agent.agents.tools.code_interpreter import extract_code  # NOQA

# 将一个插件的关键信息拼接成一段文本的模版。
TOOL_DESC = """{name_for_model}: Call this tool to interact with the {name_for_human} API. What is the {name_for_human} API useful for? {description_for_model} Parameters: {parameters}"""

# ReAct prompting 的 instruction 模版，将包含插件的详细信息。
PROMPT_REACT = """Answer the following questions as best you can. You have access to the following tools:

{tools_text}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tools_name_text}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {query}"""


#
# 本示例代码的入口函数。
#
# 输入：
#   prompt: 用户的最新一个问题。
#   history: 用户与模型的对话历史，是一个 list，
#       list 中的每个元素为 {"user": "用户输入", "bot": "模型输出"} 的一轮对话。
#       最新的一轮对话放 list 末尾。不包含最新一个问题。
#   list_of_plugin_info: 候选插件列表，是一个 list，list 中的每个元素为一个插件的关键信息。
#       比如 list_of_plugin_info = [plugin_info_0, plugin_info_1, plugin_info_2]，
#       其中 plugin_info_0, plugin_info_1, plugin_info_2 这几个样例见本文档前文。
#
# 输出：
#   模型对用户最新一个问题的回答。
#
def llm_with_plugin(prompt: str, history, list_of_plugin_info=(), prompt_tmp='default'):
    chat_history = [(x['user'], x['bot']) for x in history] + [(prompt, '')]

    # 需要让模型进行续写的初始文本
    planning_prompt = build_input_text(chat_history, list_of_plugin_info, prompt_tmp)

    text = ''
    while True:
        output = text_completion(planning_prompt + text, stop_words=['Observation:', 'Observation:\n'])
        action, action_input, output = parse_latest_plugin_call(output)
        if action:  # 需要调用插件
            # action、action_input 分别为需要调用的插件代号、输入参数
            # observation是插件返回的结果，为字符串
            observation = call_plugin(action, action_input)
            output += f'\nObservation: {observation}\nThought:'
            text += output
        else:  # 生成结束，并且不再需要调用插件
            text += output
            break

    new_history = []
    new_history.extend(history)
    new_history.append({'user': prompt, 'bot': text})
    return text, new_history


def extract_urls(text):
    pattern = re.compile(r'https?://\S+')
    urls = re.findall(pattern, text)
    return urls


def extract_obs(text):
    k = text.rfind('\nObservation:')
    j = text.rfind('\nThought:')
    obs = text[k+len('\nObservation:'):j]
    return obs.strip()


def format_answer(text):
    action, action_input, output = parse_latest_plugin_call(text)
    print('==format_answer==')
    print('action: ', action)
    print('action input: ', action_input)
    print('output: ',  output)
    # 分析生成的结果
    if 'code_interpreter' in text:
        rsp = ''
        # 获取code
        code = extract_code(action_input)
        rsp += ('\n```py\n' + code + '\n```\n')
        obs = extract_obs(text)
        if '![fig' in obs:
            rsp += obs
        return rsp
    elif 'image_gen' in text:
        # get url of FA
        # img_url = URLExtract().find_urls(text.split("Final Answer:")[-1].strip())
        img_url = extract_urls(text.split('Final Answer:')[-1].strip())
        print(img_url)
        rsp = ''
        for x in img_url:
            rsp += '\n![picture]('+x.strip()+')'
        return rsp
    else:
        return text.split('Final Answer:')[-1].strip()


# 将对话历史、插件信息聚合成一段初始文本
def build_input_text(chat_history, list_of_plugin_info, prompt_tmp='default') -> str:
    # 候选插件的详细信息
    tools_text = []
    for plugin_info in list_of_plugin_info:
        tool = TOOL_DESC.format(
            name_for_model=plugin_info['name_for_model'],
            name_for_human=plugin_info['name_for_human'],
            description_for_model=plugin_info['description_for_model'],
            parameters=json.dumps(plugin_info['parameters'], ensure_ascii=False),
        )
        if plugin_info.get('args_format', 'json') == 'json':
            tool += ' Format the arguments as a JSON object.'
        elif plugin_info['args_format'] == 'code':
            tool += ' Enclose the code within triple backticks (`) at the beginning and end of the code.'
        else:
            raise NotImplementedError
        tools_text.append(tool)
    tools_text = '\n\n'.join(tools_text)

    # 候选插件的代号
    tools_name_text = ', '.join([plugin_info['name_for_model'] for plugin_info in list_of_plugin_info])

    im_start = '<|im_start|>'
    im_end = '<|im_end|>'
    prompt = f'{im_start}system\nYou are a helpful assistant.{im_end}'
    for i, (query, response) in enumerate(chat_history):
        if list_of_plugin_info:  # 如果有候选插件
            # 倒数第一轮或倒数第二轮对话填入详细的插件信息，但具体什么位置填可以自行判断
            if (len(chat_history) == 1) or (i == len(chat_history) - 2):
                if prompt_tmp == 'default':
                    query = PROMPT_REACT.format(
                        tools_text=tools_text,
                        tools_name_text=tools_name_text,
                        query=query,
                    )
                else:
                    query = prompt_tmp.format(
                        tools_text=tools_text,
                        tools_name_text=tools_name_text,
                        query=query,
                    )
                    print(query)
        query = query.lstrip('\n').rstrip()  # 重要！若不 strip 会与训练时数据的构造方式产生差异。
        response = response.lstrip('\n').rstrip()  # 重要！若不 strip 会与训练时数据的构造方式产生差异。
        # 使用续写模式（text completion）时，需要用如下格式区分用户和AI：
        prompt += f'\n{im_start}user\n{query}{im_end}'
        prompt += f'\n{im_start}assistant\n{response}{im_end}'

    assert prompt.endswith(f'\n{im_start}assistant\n{im_end}')
    prompt = prompt[: -len(f'{im_end}')]
    return prompt


def text_completion(input_text: str, stop_words) -> str:  # 作为一个文本续写模型来使用
    im_end = '<|im_end|>'
    if im_end not in stop_words:
        stop_words = stop_words + [im_end]
    # stop_words_ids = [tokenizer.encode(w) for w in stop_words]

    # # TODO: 增加流式输出的样例实现
    # input_ids = torch.tensor([tokenizer.encode(input_text)]).to(model.device)
    # output = model.generate(input_ids, stop_words_ids=stop_words_ids)
    # output = output.tolist()[0]
    # output = tokenizer.decode(output, errors="ignore")
    # assert output.startswith(input_text)
    # output = output[len(input_text) :].replace('<|endoftext|>', '').replace(im_end, '')

    output = qwen_chat_no_stream(input_text, stop_words=stop_words)
    output = output.replace('<|endoftext|>', '').replace(im_end, '')
    for stop_str in stop_words:
        idx = output.find(stop_str)
        if idx != -1:
            output = output[: idx + len(stop_str)]
    return output  # 续写 input_text 的结果，不包含 input_text 的内容


def parse_latest_plugin_call(text):
    plugin_name, plugin_args = '', ''
    i = text.rfind('\nAction:')
    j = text.rfind('\nAction Input:')
    k = text.rfind('\nObservation:')
    if 0 <= i < j:  # If the text has `Action` and `Action input`,
        if k < j:  # but does not contain `Observation`,
            # then it is likely that `Observation` is ommited by the LLM,
            # because the output text may have discarded the stop word.
            text = text.rstrip() + '\nObservation:'  # Add it back.
        k = text.rfind('\nObservation:')
        plugin_name = text[i + len('\nAction:'):j].strip()
        plugin_args = text[j + len('\nAction Input:'):k].strip()
        text = text[:k]
    return plugin_name, plugin_args, text


#
# 输入：
#   plugin_name: 需要调用的插件代号，对应 name_for_model。
#   plugin_args：插件的输入参数，是一个 dict，dict 的 key、value 分别为参数名、参数值。
# 输出：
#   插件的返回结果，需要是字符串。
#   即使原本是 JSON 输出，也请 json.dumps(..., ensure_ascii=False) 成字符串。
#
def call_plugin(plugin_name: str, plugin_args: str) -> str:
    if plugin_name == 'code_interpreter':
        return code_interpreter(plugin_args)
    elif plugin_name == 'google_search':
        return google_search(plugin_args)
    elif plugin_name == 'image_gen':
        return image_gen(plugin_args)
    else:
        raise NotImplementedError


class Plugin(Action):
    def __init__(self, llm=None, stream=False, list_of_plugin_info=[], prompt='default'):
        super().__init__(llm=llm, stream=stream)

        self.list_of_plugin_info = list_of_plugin_info
        self.history = []
        self.prompt = prompt

    def run(self, user_request, history=[], ref_doc=None, messages=None):
        answer, history = llm_with_plugin(user_request, history=history, list_of_plugin_info=self.list_of_plugin_info, prompt_tmp=self.prompt)

        return answer


def test():
    tools = [
        {
            'name_for_human': '谷歌搜索',
            'name_for_model': 'google_search',
            'description_for_model': '谷歌搜索是一个通用搜索引擎，可用于访问互联网、查询百科知识、了解时事新闻等。',
            'parameters': [
                {
                    'name': 'search_query',
                    'description': '搜索关键词或短语',
                    'required': True,
                    'schema': {'type': 'string'},
                }
            ],
        },
        {
            'name_for_human': '文生图',
            'name_for_model': 'image_gen',
            'description_for_model': '文生图是一个AI绘画（图像生成）服务，输入文本描述，返回根据文本作画得到的图片的URL',
            'parameters': [
                {
                    'name': 'prompt',
                    'description': '英文关键词，描述了希望图像具有什么内容',
                    'required': True,
                    'schema': {'type': 'string'},
                }
            ],
        },
    ]
    history = []
    for query in ['你好', '给我画个可爱的小猫吧，最好是黑猫']:
        print(f"User's Query:\n{query}\n")
        response, history = llm_with_plugin(prompt=query, history=history, list_of_plugin_info=tools)
        print(f"Qwen's Response:\n{response}\n")
        print(history)


if __name__ == '__main__':
    test()
