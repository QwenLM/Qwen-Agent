from __future__ import annotations

import base64
import json
import re
from typing import Dict, Tuple
from urllib import parse

ALREADY_CONVERTED_MARK = '<!-- ALREADY CONVERTED BY PARSER. -->'


def parse_action_response(response: str) -> Tuple[str, Dict]:
    """parse response of llm to get tool name and parameters

    Args:
        response (str): llm response, it should conform to some predefined format

    Returns:
        tuple[str, dict]: tuple of tool name and parameters
    """

    if 'Action' not in response or 'Action Input:' not in response:
        return None, None
    action, action_para = '', ''

    # use regular expression to get result from MRKL format
    re_pattern1 = re.compile(pattern=r'Action:([\s\S]+)Action Input:([\s\S]+)')
    res = re_pattern1.search(response)
    action = res.group(1).strip()
    action_para = res.group(2)

    parameters = json.loads(action_para.replace('\n', ''))

    return action, parameters


# 图片本地路径转换为 base64 格式
def covert_image_to_base64(image_path):
    # 获得文件后缀名
    ext = image_path.split('.')[-1]
    if ext not in ['gif', 'jpeg', 'png']:
        ext = 'jpeg'

    with open(image_path, 'rb') as image_file:
        # Read the file
        encoded_string = base64.b64encode(image_file.read())

        # Convert bytes to string
        base64_data = encoded_string.decode('utf-8')

        # 生成base64编码的地址
        base64_url = f'data:image/{ext};base64,{base64_data}'
        return base64_url


def convert_url(text, new_filename):
    # Define the pattern to search for
    # This pattern captures the text inside the square brackets, the path, and the filename
    pattern = r'!\[([^\]]+)\]\(([^)]+)\)'

    # Define the replacement pattern
    # \1 is a backreference to the text captured by the first group ([^\]]+)
    replacement = rf'![\1]({new_filename})'

    # Replace the pattern in the text with the replacement
    return re.sub(pattern, replacement, text)


def format_cover_html(bot_name, bot_description, bot_avatar):
    if bot_avatar:
        image_src = covert_image_to_base64(bot_avatar)
    else:
        image_src = '//img.alicdn.com/imgextra/i3/O1CN01YPqZFO1YNZerQfSBk_!!6000000003047-0-tps-225-225.jpg'
    return f"""
<div class="bot_cover">
    <div class="bot_avatar">
        <img src="{image_src}" />
    </div>
    <div class="bot_name">{bot_name}</div>
    <div class="bot_desp">{bot_description}</div>
</div>
"""


def format_goto_publish_html(label, zip_url, agent_user_params, disable=False):
    if disable:
        return f"""<div class="publish_link_container">
        <a class="disabled">{label}</a>
    </div>
    """
    else:
        params = {'AGENT_URL': zip_url}
        params.update(agent_user_params)
        template = 'modelscope/agent_template'
        params_str = json.dumps(params)
        link_url = f'https://www.modelscope.cn/studios/fork?target={template}&overwriteEnv={parse.quote(params_str)}'
        return f"""
    <div class="publish_link_container">
        <a href="{link_url}" target="_blank">{label}</a>
    </div>
    """


def postprocess_messages(
        message_pairs: list[list[str | tuple[str] | tuple[str, str] | None] | tuple]) -> list[list[str | dict | None]]:
    if message_pairs is None:
        return []
    processed_messages = []
    for message_pair in message_pairs:
        assert isinstance(message_pair,
                          (tuple, list)), f'Expected a list of lists or list of tuples. Received: {message_pair}'
        assert len(
            message_pair
        ) == 2, f'Expected a list of lists of length 2 or list of tuples of length 2. Received: {message_pair}'

        user_message, bot_message = message_pair

        # TODO: 是否需要进行任何其他的后处理
        processed_messages.append([
            user_message,
            bot_message,
        ])
    return processed_messages
