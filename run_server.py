import argparse
import json
import os
import signal
import stat
import subprocess
import sys
from pathlib import Path

from qwen_agent.log import logger
from qwen_agent.utils.utils import get_local_ip
from qwen_server.schema import GlobalConfig


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--model_server', type=str, default='dashscope')
    parser.add_argument('-k', '--api_key', type=str, default='')
    parser.add_argument(
        '-l',
        '--llm',
        type=str,
        default='qwen-plus',
        help='DashScope: qwen-plus, qwen-turbo, qwen-14b-chat, qwen-7b-chat.',
    )
    parser.add_argument('-s',
                        '--server_host',
                        type=str,
                        default='127.0.0.1',
                        choices=['127.0.0.1', '0.0.0.0'])
    parser.add_argument(
        '-t',
        '--max_ref_token',
        type=int,
        default=4000,
        help='the max token number of reference material',
    )
    parser.add_argument(
        '-w',
        '--workstation_port',
        type=int,
        default=7864,
        help='the port of editing workstation',
    )
    args = parser.parse_args()
    args.model_server = args.model_server.replace('0.0.0.0', '127.0.0.1')
    return args


def _fix_secure_write_for_code_interpreter(code_interpreter_ws):
    if 'linux' in sys.platform.lower():
        fname = os.path.join(code_interpreter_ws, 'test_file_permission.txt')
        if os.path.exists(fname):
            os.remove(fname)
        with os.fdopen(
                os.open(fname, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o0600),
                'w') as f:
            f.write('test')
        file_mode = stat.S_IMODE(os.stat(fname).st_mode) & 0o6677
        if file_mode != 0o0600:
            os.environ['JUPYTER_ALLOW_INSECURE_WRITES'] = '1'


def update_config(server_config, args, server_config_path):
    server_config.server.model_server = args.model_server
    server_config.server.api_key = args.api_key
    server_config.server.llm = args.llm
    server_config.server.server_host = args.server_host
    server_config.server.max_ref_token = args.max_ref_token
    server_config.server.workstation_port = args.workstation_port

    with open(server_config_path, 'w') as f:
        try:
            cfg = server_config.model_dump_json()
        except AttributeError:  # for pydantic v1
            cfg = server_config.json()
        json.dump(json.loads(cfg), f, ensure_ascii=False, indent=4)
    return server_config


def main():
    args = parse_args()
    server_config_path = Path(
        __file__).resolve().parent / 'qwen_server/server_config.json'
    with open(server_config_path, 'r') as f:
        server_config = json.load(f)
        server_config = GlobalConfig(**server_config)
    server_config = update_config(server_config, args, server_config_path)

    logger.info(server_config)

    os.makedirs(server_config.path.work_space_root, exist_ok=True)
    os.makedirs(server_config.path.database_root, exist_ok=True)
    os.makedirs(server_config.path.download_root, exist_ok=True)

    os.makedirs(server_config.path.code_interpreter_ws, exist_ok=True)
    code_interpreter_work_dir = str(
        Path(__file__).resolve().parent /
        server_config.path.code_interpreter_ws)
    os.environ['M6_CODE_INTERPRETER_WORK_DIR'] = code_interpreter_work_dir

    if args.server_host == '0.0.0.0':
        static_url = get_local_ip()
    else:
        static_url = args.server_host
    static_url = f'http://{static_url}:{server_config.server.fast_api_port}/static'
    os.environ['M6_CODE_INTERPRETER_STATIC_URL'] = static_url

    _fix_secure_write_for_code_interpreter(
        server_config.path.code_interpreter_ws)

    servers = {
        'database':
        subprocess.Popen([
            sys.executable,
            os.path.join(os.getcwd(), 'qwen_server/database_server.py')
        ]),
        'workstation':
        subprocess.Popen([
            sys.executable,
            os.path.join(os.getcwd(), 'qwen_server/workstation_server.py')
        ]),
        'assistant':
        subprocess.Popen([
            sys.executable,
            os.path.join(os.getcwd(), 'qwen_server/assistant_server.py')
        ]),
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


if __name__ == '__main__':
    main()
