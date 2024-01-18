import copy
from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent.log import logger
from qwen_agent.utils.utils import has_chinese_chars, parser_function

from .schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE, FN_ARGS,
                     FN_CALL_TEMPLATE, FN_EXIT, FN_NAME, FN_RESULT, ROLE,
                     SYSTEM, USER)


class TextCompleteNotImplError(NotImplementedError):
    pass


class ModelServiceError(Exception):
    pass


class BaseChatModel(ABC):

    def __init__(self, cfg: Optional[Dict] = None):
        self.cfg = cfg or {}
        self.generate_cfg = self.cfg.get('generate_cfg', {})
        self._flag_support_text_completion: Optional[bool] = None

    def chat(
        self,
        messages: List[Dict],
        functions: Optional[List[Dict]] = None,
        stop: Optional[List[str]] = None,
        stream: bool = True,
        delta_stream: bool = False,
    ) -> Union[List[Dict], Iterator[List[Dict]]]:
        """
        llm chat interface

        :param messages: input List[Dict] formatted messages
        :param functions: input functions
        :param stop: set the stop words
        :param stream: whether to use streaming generation
        :param delta_stream: Whether to return incrementally
            - When False: Use full return
            - When True: Use incremental return
        :return: the generated message list response by llm
            - When List[Dict]: stream=False
            - When Iterator[List[Dict]]]: stream=True
        """
        messages = copy.deepcopy(messages)
        if messages[0][ROLE] != SYSTEM:
            messages.insert(0, {ROLE: SYSTEM, CONTENT: DEFAULT_SYSTEM_MESSAGE})
        if functions:
            return self.chat_with_functions(messages=messages,
                                            functions=functions,
                                            stop=stop,
                                            stream=stream,
                                            delta_stream=delta_stream)

        messages = self._convert_fncall_to_text(messages)
        logger.debug('==== Inputted messages ===')
        logger.debug(messages)
        if stream:
            return self._chat_stream(messages,
                                     stop=stop,
                                     delta_stream=delta_stream)
        else:
            return self._chat_no_stream(messages, stop=stop)

    def chat_with_functions(
            self,
            messages: List[Dict],
            functions: Optional[List[Dict]] = None,
            stop: Optional[List[str]] = None,
            stream: bool = True,
            delta_stream: bool = False
    ) -> Union[List[Dict], Iterator[List[Dict]]]:
        # convert to chat format
        messages = self._convert_fncall_to_text(messages)

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
        if messages[0][ROLE] == SYSTEM:
            messages[0][CONTENT] += tool_system
        else:
            messages.insert(0, {ROLE: SYSTEM, CONTENT: tool_system})

        # generate response
        if self._support_text_completion():
            output = self.text_completion(
                messages=messages,
                stop=[f'{FN_RESULT}:', f'{FN_RESULT}:\n'],
                stream=stream,
                delta_stream=delta_stream)
        else:
            logger.debug('==== Inputted messages ===')
            logger.debug(messages)
            if stream:
                output = self._chat_stream(
                    messages,
                    stop=[f'{FN_RESULT}:', f'{FN_RESULT}:\n'],
                    delta_stream=delta_stream)
            else:
                output = self._chat_no_stream(
                    messages, stop=[f'{FN_RESULT}:', f'{FN_RESULT}:\n'])

        # convert to fn call format
        if isinstance(output, List):
            return self._convert_text_to_fncall(output)
        else:
            return self._wrapper_output_iterator(output)

    def _wrapper_output_iterator(self, messages: Iterator[List[Dict]]):
        for m in messages:
            yield self._convert_text_to_fncall(m)

    def text_completion(
        self,
        messages: List[Dict],
        stop: Optional[List[str]] = None,
        stream: bool = True,
        delta_stream: bool = False,
    ) -> Union[List[Dict], Iterator[List[Dict]]]:
        raise TextCompleteNotImplError

    def _support_text_completion(self) -> bool:
        if self._flag_support_text_completion is None:
            try:
                messages = [{ROLE: USER, CONTENT: 'hello'}]
                response = self.text_completion(messages)
                if not isinstance(response, List):
                    *_, last = response
                self._flag_support_text_completion = True
            except TextCompleteNotImplError:
                self._flag_support_text_completion = False
            except Exception:
                self._flag_support_text_completion = False
        return self._flag_support_text_completion

    @abstractmethod
    def _chat_stream(
        self,
        messages: List[Dict],
        stop: Optional[List[str]] = None,
        delta_stream: bool = False,
    ) -> Iterator[List[Dict]]:
        raise NotImplementedError

    @abstractmethod
    def _chat_no_stream(
        self,
        messages: List[Dict],
        stop: Optional[List[str]] = None,
    ) -> List[Dict]:
        raise NotImplementedError

    @staticmethod
    def _convert_fncall_to_text(messages: List[Dict],
                                fn_role: str = 'function') -> List[Dict]:
        new_messages = []
        for msg in messages:
            role, content = msg[ROLE], msg[CONTENT]
            content = (content or '').lstrip('\n').rstrip()
            if role in (SYSTEM, USER):
                new_messages.append({ROLE: role, CONTENT: content})
            elif role == ASSISTANT:
                fn_call = msg.get(f'{fn_role}_call', {})
                if fn_call:
                    f_name = fn_call['name']
                    f_args = fn_call['arguments']
                    if f_args.startswith('```'):  # if code snippet
                        f_args = '\n' + f_args  # for markdown rendering
                    content += f'\n{FN_NAME}: {f_name}'
                    content += f'\n{FN_ARGS}: {f_args}'
                if new_messages[-1][ROLE] == ASSISTANT:
                    new_messages[-1][CONTENT] += content
                else:
                    content = content.lstrip('\n').rstrip()
                    new_messages.append({ROLE: role, CONTENT: content})
            elif role == fn_role:
                assert new_messages[-1][ROLE] == ASSISTANT
                new_messages[-1][
                    CONTENT] += f'\n{FN_RESULT}: {content}\n{FN_EXIT}: '
            else:
                raise TypeError
        return new_messages

    @staticmethod
    def _convert_text_to_fncall(messages: List[Dict],
                                fn_role: str = 'function') -> List[Dict]:
        new_messages = []
        for msg in messages:
            role, content = msg[ROLE], msg[CONTENT]
            if role in (SYSTEM, USER):
                new_messages.append({ROLE: role, CONTENT: content})
            else:
                i = content.find(f'{FN_NAME}:')
                if i < 0:
                    content = content.lstrip('\n').rstrip()
                    new_messages.append({ROLE: ASSISTANT, CONTENT: content})
                    content = ''
                elif i > 0:
                    answer = content[:i].lstrip('\n').rstrip()
                    if answer.endswith('\n'):
                        answer = answer[:-1]
                    new_messages.append({
                        ROLE: ASSISTANT,
                        CONTENT: answer,
                    })
                    content = content[i:]

                for part in content.split(f'{FN_NAME}:'):
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
                    new_messages.append({
                        ROLE: ASSISTANT,
                        CONTENT: '',
                        f'{fn_role}_call': {
                            'name': fn_name,
                            'arguments': fn_args
                        }
                    })
                    if result or answer:  # result[1:] == '' is possible and allowed
                        new_messages.append({
                            ROLE: fn_role,
                            'name': fn_name,
                            CONTENT: result[1:]  # rm the ' ' after ':'
                        })
                    if answer and answer[1:]:
                        new_messages.append({
                            ROLE: ASSISTANT,
                            CONTENT: answer[1:]  # rm the ' ' after ':'
                        })
        return new_messages

    @staticmethod
    def _wrapper_text_to_message_list(text: str) -> List[Dict]:
        return [{ROLE: ASSISTANT, CONTENT: text}]
