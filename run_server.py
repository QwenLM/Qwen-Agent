import argparse
import json
import os
import signal
import subprocess


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--openai_api_base', type=str, default='http://127.0.0.1:7905/v1')
    parser.add_argument('--openai_api_key', type=str, default='none')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()

    # update openai_api
    openai_api = {
        'openai_api_base': args.openai_api_base,
        'openai_api_key': args.openai_api_key
    }
    with open('qwen_agent/configs/config_openai.json', 'w') as file:
        json.dump(openai_api, file)

    process1 = subprocess.Popen(['python', os.path.join(os.getcwd(), 'browser_qwen/server/main.py')])
    process2 = subprocess.Popen(['python', os.path.join(os.getcwd(), 'browser_qwen/server/app.py')])
    process3 = subprocess.Popen(['python', os.path.join(os.getcwd(), 'browser_qwen/server/app_in_browser.py')])

    def signal_handler(sig, frame):
        process1.terminate()
        process2.terminate()
        process3.terminate()

    signal.signal(signal.SIGINT, signal_handler)

    process1.wait()
    process2.wait()
    process3.wait()
