import argparse
import json
import os
import signal
import subprocess
import sys

from qwen_agent.configs import config_browserqwen


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-ms', '--model_server', type=str, default='http://127.0.0.1:7905/v1')
    parser.add_argument('-mk', '--model_key', type=str, default='none')
    parser.add_argument('-lan', '--prompt_language', type=str, default='CN', choices=['EN', 'CN'], help='the language of built-in prompt')
    parser.add_argument('-llm', '--llm', type=str, default='Qwen', choices=['Qwen'])
    parser.add_argument('-t', '--max_ref_token', type=int, default=4000, help='the max token number of reference material')

    args = parser.parse_args()

    return args


if __name__ == '__main__':
    args = parse_args()

    if not os.path.exists(config_browserqwen.work_space_root):
        os.makedirs(config_browserqwen.work_space_root)
    if not os.path.exists(config_browserqwen.cache_root):
        os.makedirs(config_browserqwen.cache_root)
    if not os.path.exists(config_browserqwen.download_root):
        os.makedirs(config_browserqwen.download_root)
    if not os.path.exists(config_browserqwen.code_interpreter_ws):
        os.makedirs(config_browserqwen.code_interpreter_ws)

    # update openai_api
    openai_api = {
        'openai_api_base': args.model_server,
        'openai_api_key': args.model_key
    }
    with open(os.path.join(config_browserqwen.work_space_root, 'config_openai.json'), 'w') as file:
        json.dump(openai_api, file)

    servers = {}
    servers['database'] = subprocess.Popen([sys.executable, os.path.join(os.getcwd(), 'qwen_server/main.py'), args.prompt_language, args.llm, str(args.max_ref_token)])
    servers['workstation'] = subprocess.Popen([sys.executable, os.path.join(os.getcwd(), 'qwen_server/app.py'), args.prompt_language, args.llm, str(args.max_ref_token)])
    servers['browser'] = subprocess.Popen([sys.executable, os.path.join(os.getcwd(), 'qwen_server/app_in_browser.py'), args.prompt_language, args.llm, str(args.max_ref_token)])

    def signal_handler(sig, frame):
        for v in servers.values():
            v.terminate()
        for k in list(servers.keys()):
            del servers[k]

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    for p in list(servers.values()):
        p.wait()
