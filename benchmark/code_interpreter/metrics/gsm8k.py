import logging
import os
import re

import numpy as np
from utils.data_utils import load_jsonl, save_jsonl

INVALID_ANS = '[invalid]'


def extract_answer(completion):

    def _get_last_digit(s):
        _PAT_LAST_DIGIT = re.compile(
            r'(?<=(\s|[\$%#{]))([+-])?(?=(\S))(0|([1-9](\d*|\d{0,2}(,\d{3})*)))?(\.\d*[1-9])?(?=(\s|[.,}]|$))')
        match = list(_PAT_LAST_DIGIT.finditer(s))
        if match:
            last_digit = match[-1].group().replace(',', '').replace('+', '')
        else:
            last_digit = None
            logging.warning(f'No digits found in {s!r}')
        return last_digit

    job_gen = completion.strip('.').replace('\n', '\\n')
    last_digit = _get_last_digit(job_gen)
    if last_digit:
        return eval(last_digit)
    else:
        return INVALID_ANS


def is_correct(completion, answer):
    gold = extract_answer(answer)
    assert gold != INVALID_ANS, 'No ground truth answer found in the document.'
    return extract_answer(completion) == gold


def eval_gsm8k_acc(output_fname):
    data_list = load_jsonl(output_fname)
    acc_res = [item['acc'] for item in data_list]
    logging.info('=' * 60)
    logging.info('{:^60}'.format('Math Acc.'))
    logging.info('=' * 60)
    logging.info('Total num={:.2f}'.format(len(acc_res)))
    logging.info('Right num={:.2f}'.format(np.sum(acc_res)))
    logging.info('Zero-shot Acc={:.2f}'.format(np.mean(acc_res) * 100))

    error_data_list = [item for item in data_list if not item['acc']]
    error_data_output_fname = os.path.splitext(output_fname)[0] + '_gsm8k_error.jsonl'
    save_jsonl(error_data_list, error_data_output_fname)

    return {'math': np.mean(acc_res) * 100}
