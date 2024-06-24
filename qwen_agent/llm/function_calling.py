import copy
import json
from abc import ABC
from typing import Dict, Iterator, List, Literal, Optional, Union

from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import ASSISTANT, FUNCTION, SYSTEM, USER, ContentItem, FunctionCall, Message


def validate_num_fncall_results(messages: List[Message]):
    fn_results = []
    i = len(messages) - 1
    while messages[i].role == FUNCTION:
        fn_results = [messages[i].name] + fn_results
        i -= 1

    fn_calls = []
    while messages[i].function_call:
        fn_calls = [messages[i].function_call.name] + fn_calls
        i -= 1

    if len(fn_calls) != len(fn_results):
        raise ValueError(f'Expecting {len(fn_calls)} function results (i.e., messages with role="function") '
                         f'but received {len(fn_results)} function results. '
                         'The number of function results must match that of the function_call messages.')
    for fc_name, fr_name in zip(fn_calls, fn_results):
        if fr_name and (fc_name != fr_name):
            raise ValueError('The function results (i.e., the messages with role="function" ) must be '
                             'put in the same order as the function_call messages. And the function names must match.'
                             f'The function results are currently {fn_results}. But {fn_calls} are expected.')


class BaseFnCallModel(BaseChatModel, ABC):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        stop = self.generate_cfg.get('stop', [])
        self.generate_cfg['stop'] = stop + [x for x in FN_STOP_WORDS if x not in stop]

    def _preprocess_messages(self, messages: List[Message], lang: Literal['en', 'zh']) -> List[Message]:
        messages = super()._preprocess_messages(messages, lang=lang)
        messages = self._preprocess_fncall_messages(messages)
        return messages

    def _preprocess_fncall_messages(self, messages: List[Message]) -> List[Message]:
        """Convert messages with function_call key and function role to assistant's content, which is
            for chat interface or text_completion interface that do not support functions.
        """
        validate_num_fncall_results(messages)
        new_messages = []
        for msg in copy.deepcopy(messages):
            role, content = msg.role, msg.content
            if role in (SYSTEM, USER):
                new_messages.append(msg)
            elif role == ASSISTANT:
                content = (content or [])
                fn_call = msg.function_call
                if fn_call:
                    f_name = fn_call.name
                    f_args = fn_call.arguments
                    if f_args.startswith('```'):  # if code snippet
                        f_args = '\n' + f_args  # for markdown rendering
                    func_content = '\n' if new_messages[-1].role == ASSISTANT else ''
                    func_content += f'{FN_NAME}: {f_name}'
                    func_content += f'\n{FN_ARGS}: {f_args}'
                    content.append(ContentItem(text=func_content))
                if new_messages[-1].role == ASSISTANT:
                    new_messages[-1].content += content
                else:
                    new_messages.append(Message(role=role, content=content))
            elif role == FUNCTION:
                assert new_messages[-1].role == ASSISTANT
                assert isinstance(content, list)
                if content:
                    assert len(content) == 1
                    assert isinstance(content[0], ContentItem)
                    f_result = content[0].text
                    assert f_result is not None
                else:
                    f_result = ''
                f_exit = f'\n{FN_EXIT}: '
                last_text_content = new_messages[-1].content[-1].text
                if last_text_content.endswith(f_exit):
                    new_messages[-1].content[-1].text = last_text_content[:-len(f_exit)]
                new_messages[-1].content += [ContentItem(text=f'\n{FN_RESULT}: {f_result}{f_exit}')]
            else:
                raise TypeError

        # Remove ': ' for continued generation of function calling,
        # because ': ' may form a single token with its following words
        if new_messages[-1].role == ASSISTANT:
            last_msg = new_messages[-1].content
            for i in range(len(last_msg) - 1, -1, -1):
                item_type, item_text = last_msg[i].get_type_and_value()
                if item_type == 'text':
                    if item_text.endswith(f'{FN_EXIT}: '):
                        last_msg[i].text = item_text[:-2]
                    break
        return new_messages

    def _chat_with_functions(
        self,
        messages: List[Message],
        functions: List[Dict],
        stream: bool,
        delta_stream: bool,
        generate_cfg: dict,
        lang: Literal['en', 'zh'],
    ) -> Union[List[Message], Iterator[List[Message]]]:
        if delta_stream:
            raise NotImplementedError
        parallel_function_calls = generate_cfg.get('parallel_function_calls', False)
        messages = self._prepend_fncall_system(
            messages=messages,
            functions=functions,
            lang=lang,
            parallel_function_calls=parallel_function_calls,
        )
        if 'parallel_function_calls' in generate_cfg:
            del generate_cfg['parallel_function_calls']
        if 'function_choice' in generate_cfg:
            if messages[-1].role == ASSISTANT:
                msg_to_cont = copy.deepcopy(messages[-1])
                if msg_to_cont.content.endswith(FN_EXIT):
                    msg_to_cont.content += ': '
                msg_to_cont.content += '\n'
                messages = messages[:-1]
            else:
                msg_to_cont = Message(role=ASSISTANT, content='')
            fn_choice = generate_cfg['function_choice']
            msg_to_cont.content += f'{FN_NAME}: {fn_choice}'
            messages = messages + [msg_to_cont]
            generate_cfg = copy.deepcopy(generate_cfg)
            del generate_cfg['function_choice']
        return self._continue_assistant_response(messages, generate_cfg=generate_cfg, stream=stream)

    def _prepend_fncall_system(
        self,
        messages: List[Message],
        functions: List[Dict],
        lang: Literal['en', 'zh'],
        parallel_function_calls: bool = False,
    ) -> List[Message]:
        tool_desc_template = FN_CALL_TEMPLATE[lang + ('_parallel' if parallel_function_calls else '')]
        tool_descs = '\n\n'.join(get_function_description(function, lang=lang) for function in functions)
        tool_names = ','.join(function.get('name', function.get('name_for_model', '')) for function in functions)
        tool_system = tool_desc_template.format(tool_descs=tool_descs, tool_names=tool_names)

        assert messages[0].role == SYSTEM
        messages = copy.deepcopy(messages[:1]) + messages[1:]
        if isinstance(messages[0].content, str):
            messages[0].content += '\n\n' + tool_system
        else:
            messages[0].content.append(ContentItem(text='\n\n' + tool_system))

        return messages

    def _continue_assistant_response(
        self,
        messages: List[Message],
        generate_cfg: dict,
        stream: bool,
    ) -> Iterator[List[Message]]:
        # Simulate text completion with chat completion
        if messages and messages[-1].role == ASSISTANT:
            assert len(messages) > 1 and messages[-2].role == USER
            assert messages[-1].function_call is None
            usr = messages[-2].content
            bot = messages[-1].content
            sep = '\n\n'
            if isinstance(usr, str) and isinstance(bot, str):
                usr = usr + sep + bot
            elif isinstance(usr, list) and isinstance(bot, list):
                usr = usr + [ContentItem(text=sep)] + bot
            else:
                raise NotImplementedError
            text_to_complete = copy.deepcopy(messages[-2])
            text_to_complete.content = usr
            messages = messages[:-2] + [text_to_complete]
        return self._chat(messages, stream=stream, delta_stream=False, generate_cfg=generate_cfg)

    def _postprocess_messages(
        self,
        messages: List[Message],
        fncall_mode: bool,
        generate_cfg: dict,
    ) -> List[Message]:
        messages = super()._postprocess_messages(messages, fncall_mode=fncall_mode, generate_cfg=generate_cfg)
        if fncall_mode:
            fn_choice = generate_cfg.get('function_choice')
            if fn_choice:
                messages = copy.deepcopy(messages)
                output = messages[0].content[0].text
                if output.lstrip().startswith(FN_ARGS):
                    # Prepend this fn_choice prefix only if the model correctly completes it
                    output = f'{FN_NAME}: {fn_choice}\n' + output
                messages[0].content[0].text = output
            messages = self._postprocess_fncall_messages(messages)
        return messages

    def _postprocess_fncall_messages(self, messages: List[Message]) -> List[Message]:
        """
        If the model calls function by built-in function call template,
        convert and display it in function_call format.
        """

        # Remove ': ' brought by continued generation of function calling
        last_msg = messages[-1].content
        for i in range(len(last_msg)):
            item_type, item_text = last_msg[i].get_type_and_value()
            if item_type == 'text':
                if item_text.startswith(': '):
                    last_msg[i].text = item_text[2:]
                elif item_text.startswith(':'):
                    last_msg[i].text = item_text[1:]
                break

        new_messages = []
        for msg in messages:
            role, content = msg.role, msg.content
            assert isinstance(content, list)

            if role in (SYSTEM, USER):
                new_messages.append(Message(role=role, content=content))
                continue

            new_content = []
            for item in content:
                item_type, item_text = item.get_type_and_value()

                if item_type != 'text':  # multimodal
                    new_content.append(item)
                    continue

                for stop_word in [FN_RESULT, FN_EXIT]:
                    assert stop_word in FN_STOP_WORDS
                    assert stop_word not in item_text, 'Something wrong, stop words are expected to be excluded.'

                i = item_text.find(f'{FN_NAME}:')

                # If no function call:
                if i < 0:
                    show_text = remove_incomplete_special_tokens(item_text)
                    if show_text:
                        new_content.append(ContentItem(text=show_text))
                    continue

                # If it says something before function call:
                if i > 0:
                    answer = item_text[:i].lstrip('\n').rstrip()
                    if answer.endswith('\n'):
                        answer = answer[:-1]
                    show_text = remove_incomplete_special_tokens(answer)
                    if show_text:
                        new_content.append(ContentItem(text=show_text))
                    if new_content:
                        new_messages.append(Message(
                            role=role,
                            content=new_content,
                        ))  # split thought and function call
                        new_content = []
                    item_text = item_text[i:]

                # If has function call:
                for part in item_text.split(f'{FN_NAME}:'):
                    if not part:
                        continue
                    if part.endswith('\n'):
                        part = part[:-1]

                    arg_sep = f'\n{FN_ARGS}:'
                    i = part.find(arg_sep)
                    if i < 0:
                        fn_name = part.strip()
                        list_of_fn_args = ['']
                    else:
                        fn_name = part[:i].strip()
                        list_of_fn_args = [_.strip() for _ in part[i + len(arg_sep):].split(arg_sep)]
                    fn_name = remove_incomplete_special_tokens(fn_name)
                    for fn_args in list_of_fn_args:
                        fn_args = remove_incomplete_special_tokens(fn_args)
                        fn_args = remove_trailing_comment_of_fn_args(fn_args)
                        new_messages.append(
                            Message(
                                role=ASSISTANT,
                                content=[],
                                function_call=FunctionCall(
                                    name=fn_name,
                                    arguments=fn_args,
                                ),
                            ))
                # Break here and discard the text after function call
                return new_messages

            if new_content:
                new_messages.append(Message(role=role, content=new_content))
        return new_messages


FN_NAME = '✿FUNCTION✿'
FN_ARGS = '✿ARGS✿'
FN_RESULT = '✿RESULT✿'
FN_EXIT = '✿RETURN✿'
FN_STOP_WORDS = [FN_RESULT, FN_EXIT]

FN_CALL_TEMPLATE_INFO_ZH = """# 工具

## 你拥有如下工具：

{tool_descs}"""

FN_CALL_TEMPLATE_INFO_EN = """# Tools

## You have access to the following tools:

{tool_descs}"""

FN_CALL_TEMPLATE_FMT_ZH = """## 你可以在回复中插入零次、一次或多次以下命令以调用工具：

%s: 工具名称，必须是[{tool_names}]之一。
%s: 工具输入
%s: 工具结果
%s: 根据工具结果进行回复，需将图片用![](url)渲染出来""" % (
    FN_NAME,
    FN_ARGS,
    FN_RESULT,
    FN_EXIT,
)

FN_CALL_TEMPLATE_FMT_EN = """## When you need to call a tool, please insert the following command in your reply, which can be called zero or multiple times according to your needs:

%s: The tool to use, should be one of [{tool_names}]
%s: The input of the tool
%s: Tool results
%s: Reply based on tool results. Images need to be rendered as ![](url)""" % (
    FN_NAME,
    FN_ARGS,
    FN_RESULT,
    FN_EXIT,
)

FN_CALL_TEMPLATE_FMT_PARA_ZH = """## 你可以在回复中插入以下命令以并行调用N个工具：

%s: 工具1的名称，必须是[{tool_names}]之一
%s: 工具1的输入
%s: 工具2的名称
%s: 工具2的输入
...
%s: 工具N的名称
%s: 工具N的输入
%s: 工具1的结果
%s: 工具2的结果
...
%s: 工具N的结果
%s: 根据工具结果进行回复，需将图片用![](url)渲染出来""" % (
    FN_NAME,
    FN_ARGS,
    FN_NAME,
    FN_ARGS,
    FN_NAME,
    FN_ARGS,
    FN_RESULT,
    FN_RESULT,
    FN_RESULT,
    FN_EXIT,
)

FN_CALL_TEMPLATE_FMT_PARA_EN = """## Insert the following command in your reply when you need to call N tools in parallel:

%s: The name of tool 1, should be one of [{tool_names}]
%s: The input of tool 1
%s: The name of tool 2
%s: The input of tool 2
...
%s: The name of tool N
%s: The input of tool N
%s: The result of tool 1
%s: The result of tool 2
...
%s: The result of tool N
%s: Reply based on tool results. Images need to be rendered as ![](url)""" % (
    FN_NAME,
    FN_ARGS,
    FN_NAME,
    FN_ARGS,
    FN_NAME,
    FN_ARGS,
    FN_RESULT,
    FN_RESULT,
    FN_RESULT,
    FN_EXIT,
)

FN_CALL_TEMPLATE = {
    'zh': FN_CALL_TEMPLATE_INFO_ZH + '\n\n' + FN_CALL_TEMPLATE_FMT_ZH,
    'en': FN_CALL_TEMPLATE_INFO_EN + '\n\n' + FN_CALL_TEMPLATE_FMT_EN,
    'zh_parallel': FN_CALL_TEMPLATE_INFO_ZH + '\n\n' + FN_CALL_TEMPLATE_FMT_PARA_ZH,
    'en_parallel': FN_CALL_TEMPLATE_INFO_EN + '\n\n' + FN_CALL_TEMPLATE_FMT_PARA_EN,
}


def get_function_description(function: Dict, lang: Literal['en', 'zh']) -> str:
    """
    Text description of function
    """
    tool_desc_template = {
        'zh': '### {name_for_human}\n\n{name_for_model}: {description_for_model} 输入参数：{parameters} {args_format}',
        'en': '### {name_for_human}\n\n{name_for_model}: {description_for_model} Parameters: {parameters} {args_format}'
    }
    tool_desc = tool_desc_template[lang]
    name = function.get('name', None)
    name_for_human = function.get('name_for_human', name)
    name_for_model = function.get('name_for_model', name)
    assert name_for_human and name_for_model

    if name_for_model == 'code_interpreter':
        args_format = {
            'zh': '此工具的输入应为Markdown代码块。',
            'en': 'Enclose the code within triple backticks (`) at the beginning and end of the code.',
        }
    else:
        args_format = {
            'zh': '此工具的输入应为JSON对象。',
            'en': 'Format the arguments as a JSON object.',
        }
    args_format = function.get('args_format', args_format[lang])

    return tool_desc.format(name_for_human=name_for_human,
                            name_for_model=name_for_model,
                            description_for_model=function['description'],
                            parameters=json.dumps(function['parameters'], ensure_ascii=False),
                            args_format=args_format).rstrip()


# Mainly for removing incomplete trailing special tokens when streaming the output
def remove_incomplete_special_tokens(text: str) -> str:
    special_tokens = (FN_NAME, FN_ARGS, FN_RESULT, FN_EXIT)
    text = text.rstrip()
    if text.endswith(special_tokens):
        for s in special_tokens:
            if text.endswith(s):
                text = text[:-len(s)]
                break
    else:
        trail_start = text.rfind('✿')
        trail_token = text[trail_start:]
        for s in special_tokens:
            if s.startswith(trail_token):
                text = text[:trail_start]
                break
    text = text.lstrip('\n').rstrip()
    return text


# For hotfix badcases such as `{"arg1": "value1"} <!-- this is an example comment -->`.
def remove_trailing_comment_of_fn_args(fn_args: str):
    fn_args = fn_args.strip()

    if fn_args.startswith('{'):
        k = fn_args.rfind('}')
        if k > 0:
            fn_args = fn_args[:k + 1]

    if fn_args.startswith('```'):
        k = fn_args.rfind('\n```')
        if k > 0:
            fn_args = fn_args[:k + 4]

    return fn_args
