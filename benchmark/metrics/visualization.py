import logging
import os
import re

import torch

from config import get_model, get_react_parser
from utils.data_utils import load_jsonl, save_jsonl

torch.manual_seed(1234)


EVAL_VISUAL_PROMPT_ZH = """请判断图片是否与下面的[问题]一致，如果一致则回复“right”，不一致则回复“wrong”。
[问题]：{query}
"""

EVAL_VISUAL_PROMPT_EN = """Please judge whether the image is consistent with the [Question] below, if it is consistent then reply "right", if not then reply "wrong".
[Question]: {query}
"""


def qwen_vl_inference(qwen_vl, imgs=[], prompt=''):
    inputs = []
    for img in imgs:
        inputs.append({'image': img})

    inputs.append({'text': prompt})
    logging.info('Eval'.center(60, '-'))
    logging.info(inputs)
    query = qwen_vl.tokenizer.from_list_format(inputs)
    response, history = qwen_vl.model.chat(qwen_vl.tokenizer, query=query, history=None)
    logging.info(response)
    logging.info('='*60)
    return response


def extract_images(text):
    regex = re.compile(r'!\[fig-(.+)\]\((.+)\)')
    results = re.findall(regex, text)
    images = []
    for res in results:
        assert len(res) == 2
        if os.path.exists(res[1]):
            images.append(res[1])
    return images


def check_images_observation(text, images, model_name):
    start_flag = get_react_parser(model_name).observation
    for image in images:
        logging.info('Image'.center(60, '-'))
        logging.info(image)

        end_idx = text.find(image)
        tmp_text = text[:end_idx+len(image)]
        start_idx = tmp_text.rfind(start_flag)
        check_text = tmp_text[start_idx + len(start_flag):]

        logging.info('Observation'.center(60, '-'))
        logging.info(check_text)

        # As long as there exists correctly executed observation, we consider `True`
        if 'error:' not in check_text and 'Traceback' not in check_text:
            return True
    return False


eval_visual_prompt = {
    'zh': EVAL_VISUAL_PROMPT_ZH,
    'en': EVAL_VISUAL_PROMPT_EN
}


def eval_visualization_acc(output_fname, model_name):
    qwen_vl = get_model('qwen-vl-chat')

    one_action, one_action_right = 0, 0
    zero_action, zero_action_right = 0, 0

    data_list = load_jsonl(output_fname)
    for item in data_list:
        if 'ci_plot' not in item['tags']:
            continue

        item['vis_acc'] = False
        if '<|im_end|>' in item['query']:
            one_action += 1
            prompt = item['query'].split('<|im_end|>')[0]
        else:
            zero_action += 1
            prompt = item['query']

        images = extract_images(item['gen'])

        if images and check_images_observation(item['gen'], images, model_name):
            input_prompt = eval_visual_prompt[item.get('lang', 'en')]
            format_prompt = input_prompt.format(query=prompt)
            output = qwen_vl_inference(qwen_vl, images, format_prompt)
            if 'right' in output.lower():
                item['vis_acc'] = True
                if '<|im_end|>' in item['query']:
                    one_action_right += 1
                else:
                    zero_action_right += 1

    logging.info('*'*60)
    logging.info('{:^60}'.format('Visualization Acc.'))
    logging.info('*'*60)
    logging.info('zero action count={}, zero action right count={}, zero action acc={:.2f}'.format(zero_action, zero_action_right, zero_action_right/zero_action*100))
    logging.info('one action count={}, one action right count={}, one action acc={:.2f}'.format(one_action, one_action_right, one_action_right/one_action*100))
    logging.info('all count={}, all right={}, all acc={:.2f}'.format(zero_action+one_action, zero_action_right+one_action_right, (zero_action_right+one_action_right)/(zero_action+one_action)*100))

    error_data_list = [item for item in data_list if 'ci_plot' in item['tags'] and not item['vis_acc']]
    error_data_output_fname = os.path.splitext(output_fname)[0] + '_vis_error.jsonl'
    save_jsonl(error_data_list, error_data_output_fname)
