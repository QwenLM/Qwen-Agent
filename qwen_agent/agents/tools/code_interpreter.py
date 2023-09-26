import asyncio
import atexit
import base64
import io
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path

import json5
import matplotlib
import PIL.Image
from jupyter_client import BlockingKernelClient

sys.path.insert(
    0,
    str(Path(__file__).absolute().parent.parent.parent.parent))  # NOQA

from qwen_agent.configs import config_browserqwen  # NOQA

WORK_DIR = os.getenv('CODE_INTERPRETER_WORK_DIR', config_browserqwen.code_interpreter_ws)

LAUNCH_KERNEL_PY = """
from ipykernel import kernelapp as app
app.launch_new_instance()
"""

_KERNEL_CLIENTS = {}


def _kill_kernels():
    for v in _KERNEL_CLIENTS.values():
        v.shutdown()
    for k in list(_KERNEL_CLIENTS.keys()):
        del _KERNEL_CLIENTS[k]


atexit.register(_kill_kernels)
signal.signal(signal.SIGTERM, _kill_kernels)
signal.signal(signal.SIGINT, _kill_kernels)

# Run this fix before jupyter starts if matplotlib cannot render CJK fonts.
# And we need to additionally run the following lines in the jupyter notebook.
#   ```python
#   import matplotlib.pyplot as plt
#   plt.rcParams['font.sans-serif'] = ['SimHei']
#   plt.rcParams['axes.unicode_minus'] = False
#   ````
ali_font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'AlibabaPuHuiTi-3-45-Light.ttf')


def use_alternative_fonts(filename):
    try:
        candi_ttf = ali_font_path
        shutil.copy(candi_ttf, filename)
        print(f'Using {candi_ttf}')
    except Exception as ex:
        print(ex)


def fix_matplotlib_cjk_font_issue():
    local_ttf = os.path.join(
        os.path.abspath(
            os.path.join(matplotlib.matplotlib_fname(), os.path.pardir)),
        'fonts', 'ttf', 'simhei.ttf')
    if not os.path.exists(local_ttf):
        try:
            use_alternative_fonts(local_ttf)
        except Exception as ex:
            print(ex)

        font_list_cache = os.path.join(matplotlib.get_cachedir(),
                                       'fontlist-*.json')
        os.system(f'rm -f {font_list_cache}')


def start_kernel(pid):
    # fix_matplotlib_cjk_font_issue()

    connection_file = os.path.join(WORK_DIR,
                                   f'kernel_connection_file_{pid}.json')
    launch_kernel_script = os.path.join(WORK_DIR, f'launch_kernel_{pid}.py')
    for f in [connection_file, launch_kernel_script]:
        if os.path.exists(f):
            print(f'WARNING: {f} already exists')
            os.remove(f)

    os.makedirs(WORK_DIR, exist_ok=True)

    with open(launch_kernel_script, 'w') as fout:
        fout.write(LAUNCH_KERNEL_PY)

    kernel_process = subprocess.Popen([
        sys.executable,
        launch_kernel_script,
        '--IPKernelApp.connection_file',
        connection_file,
        '--matplotlib=inline',
        '--quiet',
    ],
        cwd=WORK_DIR)
    print(f"INFO: kernel process's PID = {kernel_process.pid}")

    # Wait for kernel connection file to be written
    while True:
        if not os.path.isfile(connection_file):
            time.sleep(0.1)
        else:
            # Keep looping if JSON parsing fails, file may be partially written
            try:
                with open(connection_file, 'r') as fp:
                    json.load(fp)
                break
            except json.JSONDecodeError:
                pass

    # Client
    kc = BlockingKernelClient(connection_file=connection_file)
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    kc.load_connection_file()
    kc.start_channels()
    kc.wait_for_ready()
    return kc


def extract_code(text):
    # Match triple backtick blocks first
    triple_match = re.search(r'```[^\n]*\n(.+?)```', text, re.DOTALL)
    if triple_match:
        text = triple_match.group(1)
    else:
        try:
            text = json5.loads(text)['code']
        except Exception:
            pass
    # If no code blocks found, return original text
    return text


def escape_ansi(line):
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)


def publish_image_to_web(image_base64: str):
    image_file = str(uuid.uuid4()) + '.png'
    local_image_file = os.path.join(WORK_DIR, image_file)

    png_bytes = base64.b64decode(image_base64)
    assert isinstance(png_bytes, bytes)
    bytes_io = io.BytesIO(png_bytes)
    PIL.Image.open(bytes_io).save(local_image_file, 'png')

    image_url = f'{config_browserqwen.fast_api_figure_url}/{image_file}'
    return image_url


START_CODE = """
import signal
def _m6_code_interpreter_timeout_handler(signum, frame):
    raise TimeoutError("M6_CODE_INTERPRETER_TIMEOUT")
signal.signal(signal.SIGALRM, _m6_code_interpreter_timeout_handler)

def input(*args, **kwargs):
    raise NotImplementedError('Python input() function is disabled.')

import os
import math
import re
import json

import seaborn as sns
sns.set_theme()

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
font_path = '{font_path}'
font_prop = FontProperties(fname=font_path)
plt.rcParams["font.family"] = font_prop.get_name()

import numpy as np
import pandas as pd

from sympy import Eq, symbols, solve
""".format(font_path=ali_font_path)
# plt.rcParams['font.sans-serif'] = ['SimHei']
# plt.rcParams['axes.unicode_minus'] = False


def code_interpreter(action_input: str, timeout=30):
    code = extract_code(action_input)
    fixed_code = []
    for line in code.split('\n'):
        fixed_code.append(line)
        if line.startswith('sns.set_theme('):
            # fixed_code.append('plt.rcParams["font.sans-serif"] = ["SimHei"]')
            # fixed_code.append('plt.rcParams["axes.unicode_minus"] = False')
            fixed_code.append('plt.rcParams["font.family"] = font_prop.get_name()')
    fixed_code = '\n'.join(fixed_code)
    return _code_interpreter(fixed_code, timeout)


def _code_interpreter(code: str, timeout):
    if not code.strip():
        return ''
    if timeout:
        code = f'signal.alarm({timeout})\n{code}'
    pid = os.getpid()
    if pid not in _KERNEL_CLIENTS:
        _KERNEL_CLIENTS[pid] = start_kernel(pid)
        _code_interpreter(START_CODE, timeout=None)
    kc = _KERNEL_CLIENTS[pid]
    kc.wait_for_ready()
    kc.execute(code)
    result = ''
    image_idx = 0
    while True:
        text = ''
        image = ''
        finished = False
        msg_type = 'error'
        try:
            msg = kc.get_iopub_msg()
            msg_type = msg['msg_type']
            if msg_type == 'status':
                if msg['content'].get('execution_state') == 'idle':
                    finished = True
            elif msg_type == 'execute_result':
                text = msg['content']['data'].get('text/plain', '')
                if 'image/png' in msg['content']['data']:
                    image_b64 = msg['content']['data']['image/png']
                    image_url = publish_image_to_web(image_b64)
                    image_idx += 1
                    image = '![fig-%03d](%s)' % (image_idx, image_url)
            elif msg_type == 'display_data':
                if 'image/png' in msg['content']['data']:
                    image_b64 = msg['content']['data']['image/png']
                    image_url = publish_image_to_web(image_b64)
                    image_idx += 1
                    image = '![fig-%03d](%s)' % (image_idx, image_url)
                else:
                    text = msg['content']['data'].get('text/plain', '')
            elif msg_type == 'stream':
                msg_type = msg['content']['name']  # stdout, stderr
                text = msg['content']['text']
            elif msg_type == 'error':
                text = escape_ansi('\n'.join(msg['content']['traceback']))
                if 'M6_CODE_INTERPRETER_TIMEOUT' in text:
                    text = f'Timeout. No response after {timeout} seconds.'
        except queue.Empty:
            text = f'Timeout. No response after {timeout} seconds.'
            finished = True
        except Exception:
            text = 'The code interpreter encountered an unexpected error.'
            print(''.join(traceback.format_exception(*sys.exc_info())))
            finished = True
        if text:
            result += f'\n\n{msg_type}:\n\n```\n{text}\n```'
        if image:
            result += f'\n\n{image}'
        if finished:
            break
    result = result.lstrip('\n')
    if timeout:
        _code_interpreter('signal.alarm(0)', timeout=None)
    return result


def get_multiline_input(hint):
    print(hint)
    print('// Press ENTER to make a new line. Press CTRL-D to end input.')
    lines = []
    while True:
        try:
            line = input()
        except EOFError:  # CTRL-D
            break
        lines.append(line)
    print('// Input received.')
    if lines:
        return '\n'.join(lines)
    else:
        return ''


if __name__ == '__main__':
    while True:
        print(code_interpreter(get_multiline_input('Enter python code:')))
