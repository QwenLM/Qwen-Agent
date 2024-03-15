import copy
from abc import ABC
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.schema import (ASSISTANT, FUNCTION, SYSTEM, USER,
                                   ContentItem, FunctionCall, Message)
from qwen_agent.utils.utils import get_function_description, has_chinese_chars


class BaseFnCallModel(BaseChatModel, ABC):

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        stop = self.generate_cfg.get('stop', [])
        self.generate_cfg['stop'] = stop + [
            x for x in FN_STOP_WORDS if x not in stop
        ]

    def _chat_with_functions(
        self,
        messages: List[Union[Message, Dict]],
        functions: List[Dict],
        stream: bool = True,
        delta_stream: bool = False
    ) -> Union[List[Message], Iterator[List[Message]]]:
        if delta_stream:
            raise NotImplementedError

        messages = self._prepend_fncall_system(messages, functions)

        # Simulate text completion with chat completion
        if messages and messages[-1].role == ASSISTANT:
            assert len(messages) > 1 and messages[-2].role == USER
            assert messages[-1].function_call is None
            usr = messages[-2].content
            bot = messages[-1].content
            if isinstance(usr, str) and isinstance(bot, str):
                usr = usr + '\n\n' + bot
            elif isinstance(usr, list) and isinstance(bot, list):
                usr = usr + [ContentItem(text='\n\n')] + bot
            else:
                raise NotImplementedError
            text_to_complete = copy.deepcopy(messages[-2])
            text_to_complete.content = usr
            messages = messages[:-2] + [text_to_complete]

        return self._chat(messages, stream=stream, delta_stream=delta_stream)

    def _preprocess_messages(self, messages: List[Message]) -> List[Message]:
        messages = super()._preprocess_messages(messages)
        messages = self._preprocess_fncall_messages(messages)
        return messages

    def _postprocess_messages(self, messages: List[Message],
                              fncall_mode: bool) -> List[Message]:
        messages = super()._postprocess_messages(messages,
                                                 fncall_mode=fncall_mode)
        if fncall_mode:
            messages = self._postprocess_fncall_messages(messages)
        return messages

    def _prepend_fncall_system(self, messages: List[Message],
                               functions: List[Dict]) -> List[Message]:
        tool_desc_template = FN_CALL_TEMPLATE['en']
        for message in messages[::-1]:
            if message.role in (USER, ):
                if has_chinese_chars(message.content):
                    tool_desc_template = FN_CALL_TEMPLATE['zh']
                break
        tool_descs = '\n\n'.join(
            get_function_description(function) for function in functions)
        tool_names = ','.join(
            function.get('name', function.get('name_for_model', ''))
            for function in functions)
        tool_system = tool_desc_template.format(tool_descs=tool_descs,
                                                tool_names=tool_names)

        assert messages[0].role == SYSTEM
        messages = copy.deepcopy(messages[:1]) + messages[1:]
        if isinstance(messages[0].content, str):
            messages[0].content += tool_system
        else:
            messages[0].content.append(ContentItem(text=tool_system))

        return messages

    def _preprocess_fncall_messages(self,
                                    messages: List[Message]) -> List[Message]:
        """Convert messages with function_call key and function role to assistant's content, which is
            for chat interface or text_completion interface that do not support functions.
        """
        new_messages = []
        for msg in copy.deepcopy(messages):
            role, content = msg.role, msg.content
            if role in (SYSTEM, USER):
                new_messages.append(msg)
            elif role == ASSISTANT:
                content = (content or [])
                fn_call = msg.function_call
                if fn_call:
                    func_content = ''
                    f_name = fn_call.name
                    f_args = fn_call.arguments
                    if f_args.startswith('```'):  # if code snippet
                        f_args = '\n' + f_args  # for markdown rendering
                    func_content += f'\n{FN_NAME}: {f_name}'
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
                new_messages[-1].content += [
                    ContentItem(text=f'\n{FN_RESULT}: {f_result}\n{FN_EXIT}: ')
                ]
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

    def _postprocess_fncall_messages(
            self,
            messages: List[Message],
            stop_at_fncall: bool = True) -> List[Message]:
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

                i = item_text.find(f'{FN_NAME}:')
                if i < 0:  # no function call
                    show_text = remove_special_tokens(item_text)
                    if show_text:
                        new_content.append(ContentItem(text=show_text))
                    continue

                if i > 0:
                    answer = item_text[:i].lstrip('\n').rstrip()
                    if answer.endswith('\n'):
                        answer = answer[:-1]
                    show_text = remove_special_tokens(answer)
                    if show_text:
                        new_content.append(ContentItem(text=show_text))
                    if new_content:
                        new_messages.append(
                            Message(
                                role=role,
                                content=new_content,
                            ))  # split thought and function call
                        new_content = []
                    item_text = item_text[i:]

                for part in item_text.split(f'{FN_NAME}:'):
                    if not part:
                        continue
                    if part.endswith('\n'):
                        part = part[:-1]
                    i = part.find(f'\n{FN_ARGS}:')
                    j = part.find(f'\n{FN_RESULT}:')
                    k = part.find(f'\n{FN_EXIT}:')
                    fn_name, fn_args, result, answer = '', '', '', ''
                    if i < 0:
                        fn_name = part.strip()
                    else:
                        fn_name = part[:i].strip()
                        if j < i:
                            fn_args = part[i + len(f'\n{FN_ARGS}:'):].strip()
                        else:
                            fn_args = part[i + len(f'\n{FN_ARGS}:'):j].strip()
                            if k < j:
                                result = part[j + len(f'\n{FN_RESULT}:'):]
                            else:
                                result = part[j + len(f'\n{FN_RESULT}:'):k]
                                answer = part[k + len(f'\n{FN_EXIT}:'):]
                    new_messages.append(
                        Message(
                            role=ASSISTANT,
                            content=[],
                            function_call=FunctionCall(
                                name=remove_special_tokens(fn_name),
                                arguments=remove_special_tokens(fn_args),
                            ),
                        ))

                    if stop_at_fncall:
                        # Discard the text after the first function_call
                        return new_messages

                    if (
                            result and result[1:]
                    ) or answer:  # result[1:] == '' is possible and allowed
                        # rm the ' ' after ':'
                        show_text = remove_special_tokens(result[1:])
                        new_messages.append(
                            Message(
                                role=FUNCTION,
                                content=[ContentItem(text=show_text)],
                                name=remove_special_tokens(fn_name),
                            ))

                    if answer and answer[1:]:
                        # rm the ' ' after ':'
                        show_text = remove_special_tokens(answer[1:])
                        if show_text:
                            new_messages.append(
                                Message(
                                    role=ASSISTANT,
                                    content=[ContentItem(text=show_text)],
                                ))
            if new_content:
                new_messages.append(Message(role=role, content=new_content))

        return new_messages


FN_NAME = '✿FUNCTION✿'
FN_ARGS = '✿ARGS✿'
FN_RESULT = '✿RESULT✿'
FN_EXIT = '✿RETURN✿'
FN_STOP_WORDS = [FN_RESULT, f'{FN_RESULT}:', f'{FN_RESULT}:\n']

FN_CALL_TEMPLATE_ZH = """

# 工具

## 你拥有如下工具：

{tool_descs}

## 你可以在回复中插入零次、一次或多次以下命令以调用工具：

%s: 工具名称，必须是[{tool_names}]之一。
%s: 工具输入
%s: 工具结果，需将图片用![](url)渲染出来。
%s: 根据工具结果进行回复""" % (
    FN_NAME,
    FN_ARGS,
    FN_RESULT,
    FN_EXIT,
)

FN_CALL_TEMPLATE_EN = """

# Tools

## You have access to the following tools:

{tool_descs}

## When you need to call a tool, please insert the following command in your reply, which can be called zero or multiple times according to your needs:

%s: The tool to use, should be one of [{tool_names}]
%s: The input of the tool
%s: The result returned by the tool. The image needs to be rendered as ![](url)
%s: Reply based on tool result""" % (
    FN_NAME,
    FN_ARGS,
    FN_RESULT,
    FN_EXIT,
)
FN_CALL_TEMPLATE = {
    'zh': FN_CALL_TEMPLATE_ZH,
    'en': FN_CALL_TEMPLATE_EN,
}


# TODO: This affects users who use the ✿ character accidentally.
# Mainly for removing incomplete trailing special tokens when streaming the output
def remove_special_tokens(text: str, strip: bool = True) -> str:
    text = text.replace('✿:', '✿')
    text = text.replace('✿：', '✿')
    out = ''
    is_special = False
    for c in text:
        if c == '✿':
            is_special = not is_special
            continue
        if is_special:
            continue
        out += c
    if strip:
        out = out.lstrip('\n').rstrip()
    return out
