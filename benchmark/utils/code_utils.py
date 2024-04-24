import os
import re

import json5


def replace_upload_fname(text, upload_fname_list):
    for full_input_fname in upload_fname_list:
        if full_input_fname not in text and os.path.basename(full_input_fname) in text:
            text = text.replace(os.path.basename(full_input_fname), full_input_fname)
    return text


def extract_code(text):
    # Match triple backtick blocks first
    triple_match = re.search(r'```[^\n]*\n(.+?)```', text, re.DOTALL)
    # Match single backtick blocks second
    single_match = re.search(r'`([^`]*)`', text, re.DOTALL)
    if triple_match:
        text = triple_match.group(1)
    elif single_match:
        text = single_match.group(1)
    else:
        try:
            text = json5.loads(text)['code']
        except Exception:
            pass
    # If no code blocks found, return original text
    return text
