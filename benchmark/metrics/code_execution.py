import logging
import os
import sys

import func_timeout
from code_interpreter import extract_code
from code_utils import replace_upload_fname
from data_utils import load_jsonl, save_jsonl
from func_timeout import func_set_timeout

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             os.path.pardir)))


pre_load = """
import os
if 'upload_file' not in os.getcwd():
    os.chdir("./workspace/upload_file/")

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
    'ci_plot': {
        'timelimit': True,
        'count_split_case': True,
    },
    'ci_math_code': {
        'timelimit': True,
        'count_split_case': False,
    },
    'ci_open_questions': {
        'timelimit': False,
        'count_split_case': True,
    }
}


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


def get_action_input_code(text, extract_first_code=False, internlm_flag=False):
    start_flag = '\nAction Input:' if not internlm_flag else '\nActionInput:'
    end_flag = '\nObservation:' if not internlm_flag else '<eoa>'
    text += '\n'
    action_input_list = []
    tmp = text
    while True:
        start = tmp.find(start_flag)
        if start == -1:
            break
        end = tmp.find(end_flag)
        action_input = tmp[start+len(start_flag):end].strip()
        action_input_list.append(action_input)
        if end == -1 or extract_first_code:
            break
        tmp = tmp[end+len(end_flag):]

    code = ''
    for action_input in action_input_list:
        code = code + '#concat\n' + extract_code(action_input).replace('/mnt/data/', '').replace('/path/to/', '') + '\n\n'
    return code


def eval_code_execution_rate(output_fname, tag='all_ci', timelimit=False, count_split_case=False, internlm_flag=False):
    data_list = load_jsonl(output_fname)
    pip_package = []

    for line_id, line in enumerate(data_list):
        line['idx'] = line_id
        tags_list = line['tags'].split(',')
        if tag not in tags_list or 'negative' in line['task']:
            continue

        # update args
        for tag in tags_list:
            if tag != 'all_ci':
                timelimit = tags_config[tag]['timelimit']
                count_split_case = tags_config[tag]['count_split_case']

        line['executable_code'] = False
        line['missing_code'] = False
        line['code_error_info'] = ''

        # get Action Input code from response
        gen_code = get_action_input_code(line['gen'], extract_first_code=count_split_case, internlm_flag=internlm_flag)

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
                    os.system('pip install '+packege)
                    logging.info(f'Automatic installation: {packege}')
                else:
                    line['code_error_info'] = str(ex)
                    break
            except Exception as ex:
                line['code_error_info'] = str(ex)
                break

        # double check
        observation = extract_first_observation(line['gen'], internlm_flag=internlm_flag)
        if line['executable_code'] and ('error:' in observation):
            logging.warning('The code executes correctly, but it has an error in IPython!')
            logging.warning(f'Code:\n{gen_code}')
            logging.warning(f'IPython error info:\n{observation}')
            logging.info('='*60)
        elif not line['executable_code'] and not ('error:' in observation):
            logging.warning('The code has an execution error, but it runs correctly in IPython!')
            logging.warning(f'Code:\n{gen_code}')
            logging.warning(f"Exec error info:\n{line['code_error_info']}")
            logging.warning(f'IPython observation:\n{observation}')
            logging.info('='*60)

    # save error data
    error_data_list = [item for item in data_list if not item['executable_code'] or item['missing_code']]
    error_data_output_fname = os.path.splitext(output_fname)[0] + '_exec_error.jsonl'
    save_jsonl(error_data_list, error_data_output_fname)

    log_result(data_list)

    return data_list


def count_error_in_observation(data_list, internlm_flag=False):
    missing_code, error_code, right_code = 0, 0, 0
    for line in data_list:
        gen = line['gen']
        gen_code = get_action_input_code(gen, extract_first_code=True, internlm_flag=internlm_flag)
        if not gen_code:
            missing_code += 1
            continue
        else:
            observation = extract_first_observation(gen, internlm_flag=internlm_flag)
            if 'error:' in observation:
                error_code += 1
            else:
                right_code += 1

    assert (missing_code + error_code + right_code) == len(data_list)
    return missing_code, error_code, right_code


def extract_first_observation(text, internlm_flag=False):
    observation = ''

    start_flag = '\nObservation:' if not internlm_flag else '<|System|>:Response:'
    end_flag = '\nThought:' if not internlm_flag else '<TOKENS_UNUSED_2>\n<|Bot|>:'

    i = text.find(start_flag)
    if i != -1:
        j = text.find(end_flag, i)
        if j != -1:
            observation = text[i+len(start_flag):j].strip()
        else:
            observation = text[i+len(start_flag):].strip()
    return observation


def log_result(data_list, verbose=True):
    if verbose:
        logging.info('*'*60)
        logging.info('{:^60}'.format('Detail'))
        logging.info('*'*60)
        for line_id, line in enumerate(data_list, start=1):
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

    logging.info('='*60)
    logging.info('{:^60}'.format('Code Execuation Rate'))
    logging.info('='*60)
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
        logging.info('Codes available && Execution Rate: {:.2f}'.format(executable_code_count/(all_count-missing_code_count)*100))
        logging.info('Execution Rate: {:.2f}'.format(executable_code_count/all_count*100))
        logging.info('Non-executable rate: {:.2f}'.format((all_count-missing_code_count-executable_code_count)/all_count*100))
        logging.info('Missing code rate: {:.2f}'.format(missing_code_count/all_count*100))

        if verbose:
            logging.info('Error List: ')
            error_list = [(item['idx'], item['code_error_info']) for item in key_item_list if item['code_error_info']]
            error_list.sort(key=lambda x: x[1])
            for x in error_list:
                logging.info(x)
