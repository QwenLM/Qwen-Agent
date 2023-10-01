import argparse
import os
import signal
import subprocess
import sys

from qwen_agent.configs import config_browserqwen


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--model_server', type=str, default='dashscope')
    parser.add_argument('-k', '--api_key', type=str, default='')
    parser.add_argument('-l', '--llm', type=str, default='qwen-turbo',
                        choices=['qwen-plus', 'qwen-turbo', 'qwen-14b-chat', 'qwen-7b-chat'])
    parser.add_argument('-lan', '--prompt_language', type=str, default='CN', choices=['EN', 'CN'],
                        help='the language of built-in prompt')  # TODO: auto detect based on query and ref
    parser.add_argument('-t', '--max_ref_token', type=int, default=3000,
                        help='the max token number of reference material')
    parser.add_argument('-w', '--workstation_port', type=int, default=7864,
                        help='the port of editing workstation')
    args = parser.parse_args()
    args.model_server = args.model_server.replace('0.0.0.0', '127.0.0.1')
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

    servers = {
        'database': subprocess.Popen(
            [sys.executable, os.path.join(os.getcwd(), 'qwen_server/main.py'), args.prompt_language, args.llm,
             str(args.max_ref_token), str(args.workstation_port), args.model_server, args.api_key]),
        'workstation': subprocess.Popen(
            [sys.executable, os.path.join(os.getcwd(), 'qwen_server/app.py'), args.prompt_language, args.llm,
             str(args.max_ref_token), str(args.workstation_port), args.model_server, args.api_key]),
        'browser': subprocess.Popen(
            [sys.executable, os.path.join(os.getcwd(), 'qwen_server/app_in_browser.py'), args.prompt_language,
             args.llm, str(args.max_ref_token), args.model_server, args.api_key])
    }

    def signal_handler(_sig, _frame):
        for v in servers.values():
            v.terminate()
        for k in list(servers.keys()):
            del servers[k]

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    for p in list(servers.values()):
        p.wait()
