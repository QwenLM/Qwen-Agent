import base64
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

visualization_code_correctness = {
    'visualization-hard': None,
    'visualization-easy': None,
}


def encode_image(image_path):
    with open(image_path, 'rb') as image_file:
        a = base64.b64encode(image_file.read()).decode('utf-8')
    return a


def judger_model_inference(judger_model_name, judger_model, imgs=[], prompt=''):
    output = ''
    if judger_model_name == 'gpt-4-vision-preview':
        logging.warning('This is an example of `gpt-4-vision-preview`. '
                        'Please set the API key and use according to your actual situation.')
        from openai import OpenAI
        client = OpenAI()
        content_list = []
        content_list.append({'type': 'text', 'text': prompt})
        input_images = []
        for img in imgs:
            if 'http' not in img:
                base64_image = encode_image(img)
                img = f'data:image/jpeg;base64,{base64_image}'
            input_images.append({'type': 'image_url', 'image_url': img})
        content_list.extend(input_images)
        response = client.chat.completions.create(
            model='gpt-4-vision-preview',
            messages=[{
                'role': 'user',
                'content': content_list,
            }],
            max_tokens=300,
        )
        output = response.choices[0]
    elif judger_model_name in ['qwen-vl-plus', 'qwen-vl-chat']:
        inputs = []
        for img in imgs:
            if 'http' not in img and judger_model_name == 'qwen-vl-plus':
                img = 'file://' + img
            inputs.append({'image': img})
        inputs.append({'text': prompt})

        logging.info('Eval'.center(60, '-'))
        logging.info(inputs)
        output = judger_model.generate(inputs)
    logging.info(output)
    logging.info('=' * 60)
    return output


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
        tmp_text = text[:end_idx + len(image)]
        start_idx = tmp_text.rfind(start_flag)
        check_text = tmp_text[start_idx + len(start_flag):]

        logging.info('Observation'.center(60, '-'))
        logging.info(check_text)

        # As long as there exists correctly executed observation, we consider `True`
        if 'error:' not in check_text and 'Traceback' not in check_text:
            return True
    return False


eval_visual_prompt = {'zh': EVAL_VISUAL_PROMPT_ZH, 'en': EVAL_VISUAL_PROMPT_EN}


def eval_visualization_acc(output_fname, model_name, judger_model_name='gpt-4-vision-preview'):
    if judger_model_name == 'gpt-4-vision-preview':
        judger_model = None
    elif judger_model_name in ['qwen-vl-chat', 'qwen-vl-plus']:
        if judger_model_name == 'qwen-vl-chat':
            logging.warning('In this benchmark of version 20231206, `Qwen-vl-chat` is no longer used as the '
                            'evaluation model for `Visualization` task.. If you insist on using it, '
                            'the evaluation results might differ from the official results.')
        judger_model = get_model(judger_model_name)
    else:
        raise Exception('Not supported judger model.')

    one_action, one_action_right = 0, 0
    zero_action, zero_action_right = 0, 0

    data_list = load_jsonl(output_fname)
    for item in data_list:
        if 'visualization' not in item['tags']:
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
            output = judger_model_inference(judger_model_name, judger_model, images, format_prompt)
            if 'right' in output.lower():
                item['vis_acc'] = True
                if '<|im_end|>' in item['query']:
                    one_action_right += 1
                else:
                    zero_action_right += 1

    logging.info('*' * 60)
    logging.info('{:^60}'.format('Visualization Acc.'))
    logging.info('*' * 60)
    logging.info('Visualization-Hard count={}, Visualization-Hard right count={}, Visualization-Hard acc={:.2f}'.format(
        zero_action, zero_action_right, zero_action_right / zero_action * 100))
    logging.info('Visualization-Easy count={}, Visualization-Easy right count={}, Visualization-Easy acc={:.2f}'.format(
        one_action, one_action_right, one_action_right / one_action * 100))
    logging.info('all count={}, all right={}, all acc={:.2f}'.format(
        zero_action + one_action, zero_action_right + one_action_right,
        (zero_action_right + one_action_right) / (zero_action + one_action) * 100))

    visualization_code_correctness['visualization-hard'] = zero_action_right / zero_action * 100
    visualization_code_correctness['visualization-easy'] = one_action_right / one_action * 100

    error_data_list = [item for item in data_list if 'visualization' in item['tags'] and not item['vis_acc']]
    error_data_output_fname = os.path.splitext(output_fname)[0] + '_vis_error.jsonl'
    save_jsonl(error_data_list, error_data_output_fname)

    return visualization_code_correctness
