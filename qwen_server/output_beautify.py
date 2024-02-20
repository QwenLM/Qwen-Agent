from typing import Dict, Iterator, List

import json5

from qwen_agent.llm.schema import (ASSISTANT, CONTENT, FUNCTION, ROLE, SYSTEM,
                                   USER)
from qwen_agent.log import logger
from qwen_agent.utils.utils import (extract_code, extract_obs, extract_urls,
                                    print_traceback)

FN_NAME = 'Action'
FN_ARGS = 'Action Input'
FN_RESULT = 'Observation'
FN_EXIT = 'Response'


def convert_fncall_to_text(messages: List[Dict]) -> List[Dict]:
    new_messages = []
    for msg in messages:
        role, content = msg[ROLE], msg[CONTENT]
        content = (content or '').lstrip('\n').rstrip()
        if role in (SYSTEM, USER):
            new_messages.append({ROLE: role, CONTENT: content})
        elif role == ASSISTANT:
            fn_call = msg.get(f'{FUNCTION}_call', {})
            if fn_call:
                f_name = fn_call['name']
                f_args = fn_call['arguments']
                if f_args.startswith('```'):  # if code snippet
                    f_args = '\n' + f_args  # for markdown rendering
                content += f'\n{FN_NAME}: {f_name}'
                content += f'\n{FN_ARGS}: {f_args}'
            if len(new_messages) > 0 and new_messages[-1][ROLE] == ASSISTANT:
                new_messages[-1][CONTENT] += content
            else:
                content = content.lstrip('\n').rstrip()
                new_messages.append({ROLE: role, CONTENT: content})
        elif role == FUNCTION:
            assert new_messages[-1][ROLE] == ASSISTANT
            new_messages[-1][
                CONTENT] += f'\n{FN_RESULT}: {content}\n{FN_EXIT}: '
        else:
            raise TypeError
    return new_messages


def format_answer(text):
    if 'code_interpreter' in text:
        rsp = ''
        code = extract_code(text)
        rsp += ('\n```py\n' + code + '\n```\n')
        obs = extract_obs(text)
        if '![fig' in obs:
            rsp += obs
        return rsp
    elif 'image_gen' in text:
        # get url of FA
        # img_urls = URLExtract().find_urls(text.split("Final Answer:")[-1].strip())
        obs = text.split(f'{FN_RESULT}:')[-1].split(f'{FN_EXIT}:')[0].strip()
        img_urls = []
        if obs:
            logger.info(repr(obs))
            try:
                obs = json5.loads(obs)
                img_urls.append(obs['image_url'])
            except Exception:
                print_traceback()
                img_urls = []
        if not img_urls:
            img_urls = extract_urls(text.split(f'{FN_EXIT}:')[-1].strip())
        logger.info(img_urls)
        rsp = ''
        for x in img_urls:
            rsp += '\n![picture](' + x.strip() + ')'
        return rsp
    else:
        return text.split(f'{FN_EXIT}:')[-1].strip()


def convert_to_full_str_stream(
        message_list_stream: Iterator[List[Dict]]) -> Iterator[str]:
    """
    output the full streaming str response
    """
    for message_list in message_list_stream:
        if not message_list:
            continue
        new_message_list = convert_fncall_to_text(message_list)
        assert len(
            new_message_list) == 1 and new_message_list[0][ROLE] == ASSISTANT
        yield new_message_list[0][CONTENT]


def convert_to_delta_str_stream(
        message_list_stream: Iterator[List[Dict]]) -> Iterator[str]:
    """
    output the delta streaming str response
    """
    last_len = 0
    delay_len = 20
    in_delay = False
    text = ''
    for text in convert_to_full_str_stream(message_list_stream):
        if (len(text) - last_len) <= delay_len:
            in_delay = True
            continue
        else:
            in_delay = False
            real_text = text[:-delay_len]
            now_rsp = real_text[last_len:]
            yield now_rsp
            last_len = len(real_text)

    if text and (in_delay or (last_len != len(text))):
        yield text[last_len:]


def convert_to_str(message_list_stream: Iterator[List[Dict]]) -> str:
    """
    output the final full str response
    """
    response = ''
    for r in convert_to_full_str_stream(message_list_stream):
        response = r
    return response
