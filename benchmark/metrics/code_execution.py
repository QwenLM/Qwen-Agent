import logging
import os

import func_timeout
from config import get_react_parser
from func_timeout import func_set_timeout
from utils.code_utils import extract_code, replace_upload_fname
from utils.data_utils import load_jsonl, save_jsonl

pre_load = """
import os
if 'upload_file' not in os.getcwd():
    os.chdir("./upload_file/")

import seaborn as sns

import matplotlib
# matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.ion()

import numpy as np
import pandas as pd
from sympy import Eq, symbols, solve
import re
import json
import math
"""

tags_config = {
    'visualization': {
        'timelimit': True,
        'extract_first_code': True,
    },
    'math': {
        'timelimit': True,
        'extract_first_code': False,
    },
    'general': {
        'timelimit': False,
        'extract_first_code': True,
    }
}

code_executability = {'math': None, 'visualization': None, 'general': None}


@func_set_timeout(10)
def exec_limit_time(text):
    exec(text, locals())


def exec_code(text, timelimit=False):
    if timelimit:
        exec_limit_time(text)
    else:
        exec(text, locals())


def postprocess_code(gen_code, line):
    if '<|im_start|>' in line['query']:
        first_action_code = get_action_input_code(line['query'])
        gen_code = first_action_code + gen_code

    upload_fname_list = line['input_file_path'] if line and 'input_file_path' in line else []
    gen_code = replace_upload_fname(gen_code, upload_fname_list)

    if 'def solution()' in gen_code:
        gen_code += '\nsolution()\n'

    if 'plt.show()' in gen_code:
        gen_code += "\nplt.pause(1)\nplt.close('all')\n"

    if 'sns.' in gen_code and 'plot' in gen_code:
        gen_code += "\nplt.close('all')\n"

    gen_code = pre_load + gen_code
    return gen_code


def get_action_input_code(text, model_name='qwen-14b-chat', extract_first_code=False):
    action_input_list = []
    tmp = text
    react_parser = get_react_parser(model_name)
    while True:
        action_input = react_parser.get_first_action_input(tmp)
        if not action_input:
            break
        action_input_list.append(action_input)
        tmp = tmp.split(action_input)[1]
        if not tmp or extract_first_code:
            break

    code = ''
    for action_input in action_input_list:
        code = code + '# concat\n' + extract_code(action_input) + '\n'
    return code


def eval_code_execution_rate(output_fname,
                             tag='all_ci',
                             model_name='qwen-14b-chat',
                             timelimit=False,
                             extract_first_code=False):
    data_list = load_jsonl(output_fname)
    pip_package = []

    for line_id, line in enumerate(data_list):
        line['idx'] = line_id
        tags_list = line['tags'].split(',')
        if tag not in tags_list:
            continue

        # update args
        for cur_tag in tags_list:
            if cur_tag != 'all_ci':
                timelimit = tags_config[cur_tag]['timelimit']
                extract_first_code = tags_config[cur_tag]['extract_first_code']

        line['executable_code'] = False
        line['missing_code'] = False
        line['code_error_info'] = ''

        # get Action Input code from response
        gen_code = get_action_input_code(line['gen'], model_name=model_name, extract_first_code=extract_first_code)

        if not gen_code:
            line['missing_code'] = True
            line['code'] = ''
            line['code_error_info'] = 'missing code'
            continue

        line['code'] = gen_code
        gen_code = postprocess_code(gen_code, line)

        while True:
            try:
                exec_code(gen_code, timelimit=timelimit)
                line['executable_code'] = True
                break
            except func_timeout.exceptions.FunctionTimedOut as ex:
                line['code_error_info'] = str(ex)
                break
            except (ImportError, ModuleNotFoundError) as ex:
                try:
                    packege = str(ex).split("'")[1].strip()
                except Exception:
                    packege = ''
                if packege and packege not in pip_package:  # install package
                    pip_package.append(packege)
                    os.system('pip install ' + packege)
                    logging.info(f'Automatic installation: {packege}')
                else:
                    line['code_error_info'] = str(ex)
                    break
            except Exception as ex:
                line['code_error_info'] = str(ex)
                break

        # double check
        observation = get_react_parser(model_name).get_first_observation(line['gen'])
        if line['executable_code'] and ('error:' in observation):
            logging.warning('The code executes correctly, but it has an error in IPython!')
            logging.warning(f'Code:\n{gen_code}')
            logging.warning(f'IPython error info:\n{observation}')
            logging.info('=' * 60)
        elif not line['executable_code'] and not ('error:' in observation):
            logging.warning('The code has an execution error, but it runs correctly in IPython!')
            logging.warning(f'Code:\n{gen_code}')
            logging.warning(f"Exec error info:\n{line['code_error_info']}")
            logging.warning(f'IPython observation:\n{observation}')
            logging.info('=' * 60)

    # save error data
    error_data_list = [item for item in data_list if not item['executable_code'] or item['missing_code']]
    error_data_output_fname = os.path.splitext(output_fname)[0] + '_exec_error.jsonl'
    save_jsonl(error_data_list, error_data_output_fname)

    log_result(data_list)

    return code_executability


def log_result(data_list, verbose=True):
    if verbose:
        logging.info('*' * 60)
        logging.info('{:^60}'.format('Detail'))
        logging.info('*' * 60)
        for line_id, line in enumerate(data_list):
            logging.info(f'Question {line_id}'.center(60, '='))
            logging.info(line['query'])

            logging.info(f'Generated {line_id}'.center(60, '-'))
            logging.info('\n' + line['gen'])

            logging.info(f'Code {line_id}'.center(60, '-'))
            logging.info('\n' + line['code'])

            logging.info(f'Exec Result {line_id}'.center(60, '-'))
            prefix_info = 'Exec Success' if line['executable_code'] else 'Exec Error: '
            exec_info = prefix_info + line['code_error_info']
            logging.info(exec_info)

    logging.info('=' * 60)
    logging.info('{:^60}'.format('Code Execuation Rate'))
    logging.info('=' * 60)
    involved_tags = []
    for line in data_list:
        involved_tags += line['tags'].split(',')
    involved_tags = list(set(involved_tags))

    for key in involved_tags:
        logging.info(f'task: {key}'.center(60, '='))
        key_item_list = [item for item in data_list if key in item['tags']]
        all_count = len(key_item_list)
        missing_code_count = len([item for item in key_item_list if item['missing_code']])
        executable_code_count = len([item for item in key_item_list if item['executable_code']])

        logging.info(f'All Test: {all_count}')
        logging.info(f'Missing Code: {missing_code_count}')
        logging.info(f'Predict Exec Success: {executable_code_count}')
        logging.info('Codes available && Execution Rate: {:.2f}'.format(executable_code_count /
                                                                        (all_count - missing_code_count) * 100))
        logging.info('Execution Rate: {:.2f}'.format(executable_code_count / all_count * 100))
        logging.info('Non-executable rate: {:.2f}'.format(
            (all_count - missing_code_count - executable_code_count) / all_count * 100))
        logging.info('Missing code rate: {:.2f}'.format(missing_code_count / all_count * 100))

        if key != 'all_ci':
            code_executability[key] = executable_code_count / all_count * 100

        if verbose:
            logging.info('Error List: ')
            error_list = [(item['idx'], item['code_error_info']) for item in key_item_list if item['code_error_info']]
            error_list.sort(key=lambda x: x[1])
            for x in error_list:
                logging.info(x)
