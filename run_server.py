import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from qwen_server.schema import GlobalConfig


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-m',
        '--model_server',
        type=str,
        default='dashscope',
        help='Set it to `dashscope` if you are using the model service provided by DashScope.'
        ' Set it to the base_url (aka api_base) if using an OpenAI API-compatible service such as vLLM or Ollama.'
        ' Default: dashscope',
    )
    parser.add_argument(
        '-k',
        '--api_key',
        type=str,
        default='',
        help='You API key to DashScope or the OpenAI API-compatible model service.',
    )
    parser.add_argument(
        '-l',
        '--llm',
        type=str,
        default='qwen-plus',
        help='Set it to one of {"qwen-max", "qwen-plus", "qwen-turbo"} if using DashScope.'
        ' Set it to the model name using an OpenAI API-compatible model service.'
        ' Default: qwen-plus',
    )
    parser.add_argument(
        '-s',
        '--server_host',
        type=str,
        default='127.0.0.1',
        choices=['127.0.0.1', '0.0.0.0'],
        help='Set to 0.0.0.0 if you want to allow other machines to access the server. Default: 127.0.0.1',
    )
    parser.add_argument(
        '-t',
        '--max_ref_token',
        type=int,
        default=4000,
        help='Tokens reserved for the reference materials of retrieval-augmanted generation (RAG). Default: 4000',
    )
    parser.add_argument(
        '-w',
        '--workstation_port',
        type=int,
        default=7864,
        help='The port of the creative writing workstation. Default: 7864',
    )
    args = parser.parse_args()
    args.model_server = args.model_server.replace('0.0.0.0', '127.0.0.1')
    return args


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
    server_config_path = Path(__file__).resolve().parent / 'qwen_server/server_config.json'
    with open(server_config_path, 'r') as f:
        server_config = json.load(f)
        server_config = GlobalConfig(**server_config)
    server_config = update_config(server_config, args, server_config_path)

    os.makedirs(server_config.path.work_space_root, exist_ok=True)
    os.makedirs(server_config.path.download_root, exist_ok=True)

    os.makedirs(server_config.path.code_interpreter_ws, exist_ok=True)
    code_interpreter_work_dir = str(Path(__file__).resolve().parent / server_config.path.code_interpreter_ws)

    # TODO: Remove these two hacky code interpreter env vars.
    os.environ['M6_CODE_INTERPRETER_WORK_DIR'] = code_interpreter_work_dir

    from qwen_agent.utils.utils import append_signal_handler, get_local_ip, logger
    logger.info(server_config)

    if args.server_host == '0.0.0.0':
        static_url = get_local_ip()
    else:
        static_url = args.server_host
    static_url = f'http://{static_url}:{server_config.server.fast_api_port}/static'
    os.environ['M6_CODE_INTERPRETER_STATIC_URL'] = static_url

    servers = {
        'database':
            subprocess.Popen([
                sys.executable,
                os.path.join(os.getcwd(), 'qwen_server/database_server.py'),
            ]),
        'workstation':
            subprocess.Popen([
                sys.executable,
                os.path.join(os.getcwd(), 'qwen_server/workstation_server.py'),
            ]),
        'assistant':
            subprocess.Popen([
                sys.executable,
                os.path.join(os.getcwd(), 'qwen_server/assistant_server.py'),
            ]),
    }

    def signal_handler(sig_num, _frame):
        for v in servers.values():
            v.terminate()
        for k in list(servers.keys()):
            del servers[k]
        if sig_num == signal.SIGINT:
            raise KeyboardInterrupt()

    append_signal_handler(signal.SIGINT, signal_handler)
    append_signal_handler(signal.SIGTERM, signal_handler)

    for p in list(servers.values()):
        p.wait()


if __name__ == '__main__':
    main()
