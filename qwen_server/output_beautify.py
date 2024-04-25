import json5

from qwen_agent.log import logger
from qwen_agent.utils.utils import extract_code, extract_urls, print_traceback

FN_NAME = 'Action'
FN_ARGS = 'Action Input'
FN_RESULT = 'Observation'
FN_EXIT = 'Response'


def extract_obs(text):
    k = text.rfind('\nObservation:')
    j = text.rfind('\nThought:')
    obs = text[k + len('\nObservation:'):j]
    return obs.strip()


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
