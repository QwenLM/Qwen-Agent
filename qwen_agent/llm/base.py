import copy
from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.utils.utils import (get_basename_from_url, has_chinese_chars,
                                    is_image, parser_function)

from ..log import logger
from .schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE, FN_ARGS,
                     FN_CALL_TEMPLATE, FN_EXIT, FN_NAME, FN_RESULT, FUNCTION,
                     ROLE, SYSTEM, USER, ContentItem, FunctionCall, Message)

LLM_REGISTRY = {}


def register_llm(model_type):

    def decorator(cls):
        LLM_REGISTRY[model_type] = cls
        return cls

    return decorator


class ModelServiceError(Exception):
    pass


class BaseChatModel(ABC):

    def __init__(self, cfg: Optional[Dict] = None):
        self.cfg = cfg or {}
        self.generate_cfg = self.cfg.get('generate_cfg', {})

        stop = self.generate_cfg.get('stop', [])
        fn_stop = [f'{FN_RESULT}:', f'{FN_RESULT}:\n']
        self.generate_cfg['stop'] = stop + [
            x for x in fn_stop if x not in stop
        ]

    def chat(
        self,
        messages: List[Union[Message, Dict]],
        functions: Optional[List[Dict]] = None,
        stream: bool = True,
        delta_stream: bool = False,
    ) -> Union[List[Message], List[Dict], Iterator[List[Message]],
               Iterator[List[Dict]]]:
        """
        llm chat interface

        :param messages: input List[Message] formatted messages
        :param functions: input functions
        :param stream: whether to use streaming generation
        :param delta_stream: Whether to return incrementally
            - When False: Use full return
            - When True: Use incremental return
        :return: the generated message list response by llm
            - When List[Message]: stream=False
            - When Iterator[List[Message]]]: stream=True
        """
        messages = copy.deepcopy(messages)
        _return_message_type = 'dict'
        new_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                new_messages.append(Message(**msg))
            else:
                new_messages.append(msg)
                _return_message_type = 'message'
        messages = new_messages

        # prepend the system message
        if messages[0][ROLE] != SYSTEM:
            messages.insert(
                0,
                Message(role=SYSTEM,
                        content=[ContentItem(text=DEFAULT_SYSTEM_MESSAGE)]))

        if functions:
            output = self._chat_with_functions(messages=messages,
                                               functions=functions,
                                               stream=stream,
                                               delta_stream=delta_stream)
            if isinstance(output, list):
                output = self._postprocess_messages_for_fn_call(output)
            else:
                output = self._postprocess_messages_iterator_for_fn_call(
                    output)
        else:
            messages = self._preprocess_messages(messages)
            output = self._chat(messages,
                                stream=stream,
                                delta_stream=delta_stream)

        if isinstance(output, list):
            return self._convert_messages_to_target_type(
                output, _return_message_type)
        else:
            return self._convert_messages_iterator_to_target_type(
                output, _return_message_type)

    def _chat_with_functions(
        self,
        messages: List[Union[Message, Dict]],
        functions: Optional[List[Dict]] = None,
        stream: bool = True,
        delta_stream: bool = False
    ) -> Union[List[Message], Iterator[List[Message]]]:

        messages = self._prepend_fn_call_system(messages, functions)
        messages = self._preprocess_messages(messages)

        if messages and messages[-1][ROLE] == ASSISTANT:
            # Change the text completion to chat mode
            assert len(messages) > 1 and messages[-2][ROLE] == USER
            messages[-2][CONTENT] += '\n\n' + messages[-1][CONTENT]
            messages.pop()

        logger.debug('==== Using chat format for function call===')
        logger.debug(messages)
        return self._chat(messages, stream=stream, delta_stream=delta_stream)

    def _chat(
        self,
        messages: List[Union[Message, Dict]],
        stream: bool = True,
        delta_stream: bool = False,
    ) -> Union[List[Message], Iterator[List[Message]]]:
        if stream:
            return self._chat_stream(messages, delta_stream=delta_stream)
        else:
            return self._chat_no_stream(messages)

    @abstractmethod
    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool = False,
    ) -> Iterator[List[Message]]:
        raise NotImplementedError

    @abstractmethod
    def _chat_no_stream(
        self,
        messages: List[Message],
    ) -> List[Message]:
        raise NotImplementedError

    @staticmethod
    def _prepend_fn_call_system(
            messages: List[Message],
            functions: Optional[List[Dict]]) -> List[Message]:
        # prepend tool react prompt
        tool_desc_template = FN_CALL_TEMPLATE['en']
        for message in messages[::-1]:
            if message[ROLE] == USER:
                if has_chinese_chars(message[CONTENT]):
                    tool_desc_template = FN_CALL_TEMPLATE['zh']
                break
        tool_descs = '\n\n'.join(
            parser_function(function) for function in functions)
        tool_names = ','.join(function['name'] for function in functions)
        tool_system = tool_desc_template.format(tool_descs=tool_descs,
                                                tool_names=tool_names)
        assert messages[0].role == SYSTEM
        if isinstance(messages[0].content, str):
            messages[0].content += tool_system
        else:
            messages[0].content.append(ContentItem(text=tool_system))

        return messages

    @staticmethod
    def _format_as_multimodal_messages(
            messages: List[Message]) -> List[Message]:
        multimodal_messages = []
        for msg in messages:
            role = msg[ROLE]
            assert role in (USER, ASSISTANT, SYSTEM, FUNCTION)
            if role == FUNCTION:
                multimodal_messages.append(msg)
                continue

            content = []
            if isinstance(msg[CONTENT], str):  # if text content
                if msg[CONTENT]:
                    content = [ContentItem(text=msg[CONTENT])]
            elif isinstance(msg[CONTENT], list):  # if multimodal content
                files = []
                for item in msg[CONTENT]:
                    for k, v in item.model_dump().items():
                        if k in ('box', 'text'):
                            content.append(ContentItem(text=v))
                        if k == 'image':
                            content.append(item)
                        if k in ('file', 'image'):
                            files.append(v)
                if (msg[ROLE] in (SYSTEM, USER)) and files:
                    has_zh = has_chinese_chars(content)
                    upload = []
                    for f in [get_basename_from_url(f) for f in files]:
                        if is_image(f):
                            if has_zh:
                                upload.append(f'![图片]({f})')
                            else:
                                upload.append(f'![image]({f})')
                        else:
                            if has_zh:
                                upload.append(f'[文件]({f})')
                            else:
                                upload.append(f'[file]({f})')
                    upload = ' '.join(upload)
                    if has_zh:
                        upload = f'（上传了 {upload}）\n\n'
                    else:
                        upload = f'(Uploaded {upload})\n\n'
                    content = [ContentItem(text=upload)
                               ] + content  # insert a text
            else:
                raise TypeError

            multimodal_messages.append(
                Message(role=role,
                        content=content,
                        function_call=msg.function_call))

        return multimodal_messages

    def _preprocess_messages(self, messages: List[Message]) -> List[Message]:
        """
        Convert messages with function_call key and function role to assistant's content, which is
            for chat interface or text_completion interface that do not support functions.
        """
        messages = self._format_as_multimodal_messages(messages)

        new_messages = []
        for msg in messages:
            role, content = msg[ROLE], msg[CONTENT]
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
                if new_messages[-1][ROLE] == ASSISTANT:
                    new_messages[-1][CONTENT] += content
                else:
                    new_messages.append(Message(role=role, content=content))
            elif role == FUNCTION:
                assert new_messages[-1][ROLE] == ASSISTANT
                new_messages[-1][CONTENT] += [
                    ContentItem(text=f'\n{FN_RESULT}: {content}\n{FN_EXIT}: ')
                ]
            else:
                raise TypeError

        # remove ': ' for continued generation of function calling,
        # because ': ' may form a single token with its following words
        if new_messages[-1][ROLE] == ASSISTANT:
            for i in range(len(new_messages[-1][CONTENT]) - 1, -1, -1):
                if 'text' in new_messages[-1][CONTENT][i]:
                    last_content = new_messages[-1][CONTENT][i]['text']
                    if last_content.endswith(f'{FN_EXIT}: '):
                        new_messages[-1][CONTENT][i][
                            'text'] = last_content[:-2]
                    break
        return new_messages

    def _postprocess_messages_for_fn_call(
            self, messages: List[Message]) -> List[Message]:
        """
        If the model calls function by built-in function call template, convert and display it in function_call format in return.
        """
        messages = self._format_as_multimodal_messages(messages)

        # remove ': ' brought by continued generation of function calling
        for i in range(len(messages[0][CONTENT])):
            if 'text' in messages[0][CONTENT][i]:
                first_content = messages[0][CONTENT][i]['text']
                if first_content.startswith(': '):
                    messages[0][CONTENT][i]['text'] = first_content[2:]
                break

        new_messages = []
        for msg in messages:
            role, content = msg[ROLE], msg[CONTENT]
            assert isinstance(content, list)
            if role in (SYSTEM,
                        USER):  # Currently, it is not possible to occur
                new_messages.append(Message(role=role, content=content))
            else:
                new_content = []
                for item in content:
                    for k, v in item.model_dump().items():
                        if k == 'text':
                            tmp_content = v
                            i = tmp_content.find(f'{FN_NAME}:')
                            if i < 0:
                                new_content.append(item)
                                continue
                            elif i > 0:
                                answer = tmp_content[:i].lstrip('\n').rstrip()
                                if answer.endswith('\n'):
                                    answer = answer[:-1]
                                new_content.append(ContentItem(text=answer))
                                new_messages.append(
                                    Message(
                                        role=role,
                                        content=new_content))  # split message
                                new_content = []
                                tmp_content = tmp_content[i:]

                            for part in tmp_content.split(f'{FN_NAME}:'):
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
                                        fn_args = part[i + len(f'\n{FN_ARGS}:'
                                                               ):].strip()
                                    else:
                                        fn_args = part[i + len(f'\n{FN_ARGS}:'
                                                               ):j].strip()
                                        if k < j:
                                            result = part[j +
                                                          len(f'\n{FN_RESULT}:'
                                                              ):]
                                        else:
                                            result = part[j +
                                                          len(f'\n{FN_RESULT}:'
                                                              ):k]
                                            answer = part[k +
                                                          len(f'\n{FN_EXIT}:'
                                                              ):]
                                new_messages.append(
                                    Message(ASSISTANT, [],
                                            function_call=FunctionCall(
                                                name=fn_name,
                                                arguments=fn_args)))

                                if result or answer:  # result[1:] == '' is possible and allowed
                                    new_messages.append(
                                        Message(FUNCTION,
                                                result[1:],
                                                name=fn_name))
                                if answer and answer[1:]:
                                    new_messages.append(
                                        Message(
                                            ASSISTANT,
                                            [ContentItem(text=answer[1:])]))
                        else:
                            new_content.append(item)
                if new_content:
                    new_messages.append(Message(role,
                                                new_content))  # no func call
        return new_messages

    def _postprocess_messages_iterator_for_fn_call(
            self,
            messages: Iterator[List[Message]]) -> Iterator[List[Message]]:
        for m in messages:
            yield self._postprocess_messages_for_fn_call(m)

    def _convert_messages_to_target_type(
            self, messages: List[Message],
            target_type: str) -> Union[List[Message], List[Dict]]:
        if target_type == 'message':
            return [
                Message(**x) if isinstance(x, dict) else x for x in messages
            ]
        elif target_type == 'dict':
            return [
                x.model_dump() if not isinstance(x, dict) else x
                for x in messages
            ]
        else:
            raise NotImplementedError

    def _convert_messages_iterator_to_target_type(
        self, messages_iter: Iterator[List[Message]], target_type: str
    ) -> Union[Iterator[List[Message]], Iterator[List[Dict]]]:
        for messages in messages_iter:
            yield self._convert_messages_to_target_type(messages, target_type)
