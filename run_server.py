import argparse
import os
import signal
import stat
import subprocess
import sys

from qwen_server import config_browserqwen


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--model_server', type=str, default='dashscope')
    parser.add_argument('-k', '--api_key', type=str, default='')
    parser.add_argument('-l', '--llm', type=str, default='qwen-turbo',
                        choices=['qwen-plus', 'qwen-turbo', 'qwen-14b-chat', 'qwen-7b-chat'])
    parser.add_argument('-s', '--server_host', type=str, default='127.0.0.1')
    parser.add_argument('-lan', '--prompt_language', type=str, default='CN', choices=['EN', 'CN'],
                        help='the language of built-in prompt')  # TODO: auto detect based on query and ref
    parser.add_argument('-t', '--max_ref_token', type=int, default=4000,
                        help='the max token number of reference material')
    parser.add_argument('-w', '--workstation_port', type=int, default=7864,
                        help='the port of editing workstation')
    args = parser.parse_args()
    args.model_server = args.model_server.replace('0.0.0.0', '127.0.0.1')
    return args


def _fix_secure_write_for_code_interpreter():
    if 'linux' in sys.platform.lower():
        fname = os.path.join(config_browserqwen.code_interpreter_ws, 'test_file_permission.txt')
        if os.path.exists(fname):
            os.remove(fname)
        with os.fdopen(os.open(fname, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o0600), 'w') as f:
            f.write('test')
        file_mode = stat.S_IMODE(os.stat(fname).st_mode) & 0o6677
        if file_mode != 0o0600:
            os.environ['JUPYTER_ALLOW_INSECURE_WRITES'] = '1'


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
    _fix_secure_write_for_code_interpreter()

    servers = {
        'database': subprocess.Popen(
            [sys.executable, os.path.join(os.getcwd(), 'qwen_server/main.py'), args.prompt_language, args.llm,
             str(args.max_ref_token), str(args.workstation_port), args.model_server, args.api_key, args.server_host]),
        'workstation': subprocess.Popen(
            [sys.executable, os.path.join(os.getcwd(), 'qwen_server/app.py'), args.prompt_language, args.llm,
             str(args.max_ref_token), str(args.workstation_port), args.model_server, args.api_key, args.server_host]),
        'browser': subprocess.Popen(
            [sys.executable, os.path.join(os.getcwd(), 'qwen_server/app_in_browser.py'), args.prompt_language,
             args.llm, str(args.max_ref_token), args.model_server, args.api_key, args.server_host])
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
