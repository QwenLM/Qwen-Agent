import copy
from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.utils.utils import (get_basename_from_url, has_chinese_chars,
                                    is_image, parser_function)

from ..log import logger
from .schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE, FN_ARGS,
                     FN_CALL_TEMPLATE, FN_EXIT, FN_NAME, FN_RESULT, FUNCTION,
                     ROLE, SYSTEM, USER)


class TextCompleteNotImplError(NotImplementedError):
    pass


class ModelServiceError(Exception):
    pass


class FnCallNotImplError(NotImplementedError):
    pass


class BaseChatModel(ABC):

    def __init__(self, cfg: Optional[Dict] = None):
        self.cfg = cfg or {}
        self.generate_cfg = self.cfg.get('generate_cfg', {})
        self._flag_support_text_completion: Optional[bool] = None

        stop = self.generate_cfg.get('stop', [])
        fn_stop = [f'{FN_RESULT}:', f'{FN_RESULT}:\n']
        self.generate_cfg['stop'] = stop + [
            x for x in fn_stop if x not in stop
        ]

    def chat(
        self,
        messages: List[Dict],
        functions: Optional[List[Dict]] = None,
        stream: bool = True,
        delta_stream: bool = False,
    ) -> Union[List[Dict], Iterator[List[Dict]]]:
        """
        llm chat interface

        :param messages: input List[Dict] formatted messages
        :param functions: input functions
        :param stream: whether to use streaming generation
        :param delta_stream: Whether to return incrementally
            - When False: Use full return
            - When True: Use incremental return
        :return: the generated message list response by llm
            - When List[Dict]: stream=False
            - When Iterator[List[Dict]]]: stream=True
        """
        if functions:
            return self.chat_with_functions(messages=messages,
                                            functions=functions,
                                            stream=stream,
                                            delta_stream=delta_stream)
        messages = copy.deepcopy(messages)
        messages = self._format_msg_to_list(messages)

        if messages[0][ROLE] != SYSTEM:
            messages.insert(0, {
                ROLE: SYSTEM,
                CONTENT: [{
                    'text': DEFAULT_SYSTEM_MESSAGE
                }]
            })

        messages = self._preprocess_convert_fncall_to_text(messages)
        messages = self._format_msg_for_llm(messages)
        logger.debug('==== Preprocessed Inputted messages ===')
        logger.debug(messages)
        if stream:
            return self._chat_stream(messages, delta_stream=delta_stream)
        else:
            return self._chat_no_stream(messages)

    def chat_with_functions(
            self,
            messages: List[Dict],
            functions: Optional[List[Dict]] = None,
            stream: bool = True,
            delta_stream: bool = False
    ) -> Union[List[Dict], Iterator[List[Dict]]]:
        messages = copy.deepcopy(messages)

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
        # preprocess
        messages = self._format_msg_to_list(messages)

        if messages[0][ROLE] == SYSTEM:
            messages[0][CONTENT] += [{'text': tool_system}]
        else:
            messages.insert(
                0, {
                    ROLE: SYSTEM,
                    CONTENT: [{
                        'text': DEFAULT_SYSTEM_MESSAGE + tool_system
                    }]
                })

        messages = self._preprocess_convert_fncall_to_text(messages)
        messages = self._format_msg_for_llm(messages)

        # generate response
        if self._support_text_completion():
            output = self.text_completion(messages=messages,
                                          stream=stream,
                                          delta_stream=delta_stream)
        else:
            logger.debug('==== Inputted messages: Using chat format ===')
            logger.debug(messages)
            if stream:
                output = self._chat_stream(messages, delta_stream=delta_stream)
            else:
                output = self._chat_no_stream(messages)

        # convert to fn call format
        if isinstance(output, list):
            return self._postprocess_convert_text_to_fncall(output)
        else:
            return self._postprocess_iterator(output)

    def text_completion(
        self,
        messages: List[Dict],
        stream: bool = True,
        delta_stream: bool = False,
    ) -> Union[List[Dict], Iterator[List[Dict]]]:
        raise TextCompleteNotImplError

    @abstractmethod
    def _chat_stream(
        self,
        messages: List[Dict],
        delta_stream: bool = False,
    ) -> Iterator[List[Dict]]:
        raise NotImplementedError

    @abstractmethod
    def _chat_no_stream(
        self,
        messages: List[Dict],
    ) -> List[Dict]:
        raise NotImplementedError

    @abstractmethod
    def _format_msg_for_llm(self, messages: List[Dict]) -> List[Dict]:
        raise NotImplementedError

    def _support_text_completion(self) -> bool:
        if self._flag_support_text_completion is None:
            try:
                messages = [{ROLE: USER, CONTENT: 'hello'}]
                response = self.text_completion(messages)
                if not isinstance(response, list):
                    *_, last = response
                self._flag_support_text_completion = True
            except TextCompleteNotImplError:
                self._flag_support_text_completion = False
            except Exception:
                self._flag_support_text_completion = False
        return self._flag_support_text_completion

    def _postprocess_iterator(
            self, messages: Iterator[List[Dict]]) -> Iterator[List[Dict]]:
        for m in messages:
            yield self._postprocess_convert_text_to_fncall(m)

    @staticmethod
    def _format_msg_to_list(messages: List[Dict]) -> List[Dict]:
        new_messages = []
        for msg in messages:
            role = msg[ROLE]
            assert role in (USER, ASSISTANT, SYSTEM, FUNCTION)
            if role == FUNCTION:
                new_messages.append(msg)
                continue
            # assert f'{FUNCTION}_call' not in msg, 'assume vl does not support function'
            content = []
            if isinstance(msg[CONTENT], str):
                content = [{'text': msg[CONTENT]}]
            elif isinstance(msg[CONTENT], list):
                files = []
                for item in msg[CONTENT]:
                    for k, v in item.items():
                        if k in ('box', 'text', 'image', 'result_image'):
                            content.append(item)
                        if k in ('file', 'image'):
                            files.append(v)
                if files:
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
                        upload = f'（上传了 {upload}）'
                    else:
                        upload = f'(Uploaded {upload})'
                    content = [{'text': upload}] + content  # insert a text
            else:
                raise TypeError
            if f'{FUNCTION}_call' in msg:
                new_messages.append({
                    ROLE: role,
                    CONTENT: content,
                    f'{FUNCTION}_call': msg[f'{FUNCTION}_call']
                })
            else:
                new_messages.append({ROLE: role, CONTENT: content})

        return new_messages

    @staticmethod
    def _preprocess_convert_fncall_to_text(messages: List[Dict]) -> List[Dict]:
        """
        Convert messages with function_call key and function role to assistant's content, which is
            for chat interface or text_completion interface that do not support functions.
        """
        new_messages = []
        for msg in messages:
            role, content = msg[ROLE], msg[CONTENT]
            if role in (SYSTEM, USER):
                new_messages.append({ROLE: role, CONTENT: content})
            elif role == ASSISTANT:
                content = (content or [])
                fn_call = msg.get(f'{FUNCTION}_call', {})
                if fn_call:
                    func_content = ''
                    f_name = fn_call['name']
                    f_args = fn_call['arguments']
                    if f_args.startswith('```'):  # if code snippet
                        f_args = '\n' + f_args  # for markdown rendering
                    func_content += f'\n{FN_NAME}: {f_name}'
                    func_content += f'\n{FN_ARGS}: {f_args}'
                    content.append({'text': func_content})
                if new_messages[-1][ROLE] == ASSISTANT:
                    new_messages[-1][CONTENT] += content
                else:
                    new_messages.append({ROLE: role, CONTENT: content})
            elif role == FUNCTION:
                assert new_messages[-1][ROLE] == ASSISTANT
                new_messages[-1][CONTENT] += [{
                    'text':
                    f'\n{FN_RESULT}: {content}\n{FN_EXIT}: '
                }]
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

    def _postprocess_convert_text_to_fncall(
            self, messages: List[Dict]) -> List[Dict]:
        """
        If the model calls function by built-in function call template, convert and display it in function_call format in return.
        """
        messages = self._format_msg_to_list(messages)

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
                new_messages.append({ROLE: role, CONTENT: content})
            else:
                new_content = []
                for item in content:
                    for k, v in item.items():
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
                                new_content.append({'text': answer})
                                new_messages.append({
                                    ROLE: role,
                                    CONTENT: new_content
                                })  # split message
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
                                new_messages.append({
                                    ROLE: ASSISTANT,
                                    CONTENT: [{
                                        'text': ''
                                    }],
                                    f'{FUNCTION}_call': {
                                        'name': fn_name,
                                        'arguments': fn_args
                                    }
                                })
                                if result or answer:  # result[1:] == '' is possible and allowed
                                    new_messages.append({
                                        ROLE: FUNCTION,
                                        'name': fn_name,
                                        CONTENT:
                                        result[1:]  # rm the ' ' after ':'
                                    })
                                if answer and answer[1:]:
                                    new_messages.append({
                                        ROLE:
                                        ASSISTANT,
                                        CONTENT: [{
                                            'text': answer[1:]
                                        }]  # rm the ' ' after ':'
                                    })
                        else:
                            new_content.append(item)
                if new_content:
                    new_messages.append({
                        ROLE: role,
                        CONTENT: new_content
                    })  # no func call
        new_messages = self._format_msg_for_llm(new_messages)
        return new_messages
