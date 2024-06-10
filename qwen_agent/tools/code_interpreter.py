import asyncio
import atexit
import base64
import glob
import io
import json
import os
import queue
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import json5
import matplotlib
import PIL.Image
from jupyter_client import BlockingKernelClient

from qwen_agent.log import logger
from qwen_agent.settings import DEFAULT_WORKSPACE
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import (append_signal_handler, extract_code, has_chinese_chars, print_traceback,
                                    save_url_to_local_work_dir)

LAUNCH_KERNEL_PY = """
from ipykernel import kernelapp as app
app.launch_new_instance()
"""

INIT_CODE_FILE = str(Path(__file__).absolute().parent / 'resource' / 'code_interpreter_init_kernel.py')
ALIB_FONT_FILE = str(Path(__file__).absolute().parent / 'resource' / 'AlibabaPuHuiTi-3-45-Light.ttf')

_KERNEL_CLIENTS: Dict[str, BlockingKernelClient] = {}
_MISC_SUBPROCESSES: Dict[str, subprocess.Popen] = {}


def _kill_kernels_and_subprocesses(_sig_num=None, _frame=None):
    for v in _KERNEL_CLIENTS.values():
        v.shutdown()
    for k in list(_KERNEL_CLIENTS.keys()):
        del _KERNEL_CLIENTS[k]

    for v in _MISC_SUBPROCESSES.values():
        v.terminate()
    for k in list(_MISC_SUBPROCESSES.keys()):
        del _MISC_SUBPROCESSES[k]


# Make sure all subprocesses are terminated even if killed abnormally:
atexit.register(_kill_kernels_and_subprocesses)
append_signal_handler(signal.SIGTERM, _kill_kernels_and_subprocesses)
append_signal_handler(signal.SIGINT, _kill_kernels_and_subprocesses)


@register_tool('code_interpreter')
class CodeInterpreter(BaseTool):
    description = 'Python代码沙盒，可用于执行Python代码。'
    parameters = [{'name': 'code', 'type': 'string', 'description': '待执行的代码', 'required': True}]

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        default_work_dir = os.getenv('M6_CODE_INTERPRETER_WORK_DIR',
                                     os.path.join(DEFAULT_WORKSPACE, 'tools', 'code_interpreter'))
        self.work_dir: str = self.cfg.get('work_dir', default_work_dir)
        self.instance_id: str = str(uuid.uuid4())

    @property
    def args_format(self) -> str:
        fmt = self.cfg.get('args_format')
        if fmt is None:
            if has_chinese_chars([self.name_for_human, self.name, self.description, self.parameters]):
                fmt = '此工具的输入应为Markdown代码块。'
            else:
                fmt = 'Enclose the code within triple backticks (`) at the beginning and end of the code.'
        return fmt

    @property
    def file_access(self) -> bool:
        return True

    def call(self, params: Union[str, dict], files: List[str] = None, timeout: Optional[int] = 30, **kwargs) -> str:
        try:
            params = json5.loads(params)
            code = params['code']
        except Exception:
            code = extract_code(params)

        if not code.strip():
            return ''
        # download file
        if files:
            os.makedirs(self.work_dir, exist_ok=True)
            for file in files:
                try:
                    save_url_to_local_work_dir(file, self.work_dir)
                except Exception:
                    print_traceback()

        kernel_id: str = f'{self.instance_id}_{os.getpid()}'
        if kernel_id in _KERNEL_CLIENTS:
            kc = _KERNEL_CLIENTS[kernel_id]
        else:
            _fix_matplotlib_cjk_font_issue()
            self._fix_secure_write_for_code_interpreter()
            kc, subproc = self._start_kernel(kernel_id)
            with open(INIT_CODE_FILE) as fin:
                start_code = fin.read()
                start_code = start_code.replace('{{M6_FONT_PATH}}', repr(ALIB_FONT_FILE)[1:-1])
                start_code += '\n%xmode Minimal'
            logger.info(self._execute_code(kc, start_code))
            _KERNEL_CLIENTS[kernel_id] = kc
            _MISC_SUBPROCESSES[kernel_id] = subproc

        if timeout:
            code = f'_M6CountdownTimer.start({timeout})\n{code}'

        fixed_code = []
        for line in code.split('\n'):
            fixed_code.append(line)
            if line.startswith('sns.set_theme('):
                fixed_code.append('plt.rcParams["font.family"] = _m6_font_prop.get_name()')
        fixed_code = '\n'.join(fixed_code)
        fixed_code += '\n\n'  # Prevent code not executing in notebook due to no line breaks at the end
        result = self._execute_code(kc, fixed_code)

        if timeout:
            self._execute_code(kc, '_M6CountdownTimer.cancel()')

        return result if result.strip() else 'Finished execution.'

    def __del__(self):
        # Recycle the jupyter subprocess:
        k: str = f'{self.instance_id}_{os.getpid()}'
        if k in _KERNEL_CLIENTS:
            _KERNEL_CLIENTS[k].shutdown()
            del _KERNEL_CLIENTS[k]
        if k in _MISC_SUBPROCESSES:
            _MISC_SUBPROCESSES[k].terminate()
            del _MISC_SUBPROCESSES[k]

    def _fix_secure_write_for_code_interpreter(self):
        if 'linux' in sys.platform.lower():
            os.makedirs(self.work_dir, exist_ok=True)
            fname = os.path.join(self.work_dir, f'test_file_permission_{os.getpid()}.txt')
            if os.path.exists(fname):
                os.remove(fname)
            with os.fdopen(os.open(fname, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o0600), 'w') as f:
                f.write('test')
            file_mode = stat.S_IMODE(os.stat(fname).st_mode) & 0o6677
            if file_mode != 0o0600:
                os.environ['JUPYTER_ALLOW_INSECURE_WRITES'] = '1'
            if os.path.exists(fname):
                os.remove(fname)

    def _start_kernel(self, kernel_id: str) -> Tuple[BlockingKernelClient, subprocess.Popen]:
        connection_file = os.path.join(self.work_dir, f'kernel_connection_file_{kernel_id}.json')
        launch_kernel_script = os.path.join(self.work_dir, f'launch_kernel_{kernel_id}.py')
        for f in [connection_file, launch_kernel_script]:
            if os.path.exists(f):
                logger.info(f'WARNING: {f} already exists')
                os.remove(f)

        os.makedirs(self.work_dir, exist_ok=True)
        with open(launch_kernel_script, 'w') as fout:
            fout.write(LAUNCH_KERNEL_PY)

        kernel_process = subprocess.Popen(
            [
                sys.executable,
                os.path.abspath(launch_kernel_script),
                '--IPKernelApp.connection_file',
                os.path.abspath(connection_file),
                '--matplotlib=inline',
                '--quiet',
            ],
            cwd=os.path.abspath(self.work_dir),
        )
        logger.info(f"INFO: kernel process's PID = {kernel_process.pid}")

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
        asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
        kc.load_connection_file()
        kc.start_channels()
        kc.wait_for_ready()
        return kc, kernel_process

    def _execute_code(self, kc: BlockingKernelClient, code: str) -> str:
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
                        image_url = self._serve_image(image_b64)
                        image_idx += 1
                        image = '![fig-%03d](%s)' % (image_idx, image_url)
                elif msg_type == 'display_data':
                    if 'image/png' in msg['content']['data']:
                        image_b64 = msg['content']['data']['image/png']
                        image_url = self._serve_image(image_b64)
                        image_idx += 1
                        image = '![fig-%03d](%s)' % (image_idx, image_url)
                    else:
                        text = msg['content']['data'].get('text/plain', '')
                elif msg_type == 'stream':
                    msg_type = msg['content']['name']  # stdout, stderr
                    text = msg['content']['text']
                elif msg_type == 'error':
                    text = _escape_ansi('\n'.join(msg['content']['traceback']))
                    if 'M6_CODE_INTERPRETER_TIMEOUT' in text:
                        text = 'Timeout: Code execution exceeded the time limit.'
            except queue.Empty:
                text = 'Timeout: Code execution exceeded the time limit.'
                finished = True
            except Exception:
                text = 'The code interpreter encountered an unexpected error.'
                print_traceback()
                finished = True
            if text:
                result += f'\n\n{msg_type}:\n\n```\n{text}\n```'
            if image:
                result += f'\n\n{image}'
            if finished:
                break
        result = result.lstrip('\n')
        return result

    # TODO: Remove this buggy image service and return local_image_file directly.
    def _serve_image(self, image_base64: str) -> str:
        image_file = f'{uuid.uuid4()}.png'
        local_image_file = os.path.join(self.work_dir, image_file)

        png_bytes = base64.b64decode(image_base64)
        assert isinstance(png_bytes, bytes)
        bytes_io = io.BytesIO(png_bytes)
        PIL.Image.open(bytes_io).save(local_image_file, 'png')

        static_url = os.getenv('M6_CODE_INTERPRETER_STATIC_URL', '')

        # Hotfix: Temporarily generate image URL proxies for code interpreter to display in gradio
        if not static_url:
            return local_image_file
        else:
            image_url = f'{static_url}/{image_file}'
            return image_url


def _fix_matplotlib_cjk_font_issue():
    ttf_name = os.path.basename(ALIB_FONT_FILE)
    local_ttf = os.path.join(os.path.abspath(os.path.join(matplotlib.matplotlib_fname(), os.path.pardir)), 'fonts',
                             'ttf', ttf_name)
    if not os.path.exists(local_ttf):
        try:
            shutil.copy(ALIB_FONT_FILE, local_ttf)
            font_list_cache = os.path.join(matplotlib.get_cachedir(), 'fontlist-*.json')
            for cache_file in glob.glob(font_list_cache):
                with open(cache_file) as fin:
                    cache_content = fin.read()
                if ttf_name not in cache_content:
                    os.remove(cache_file)
        except Exception:
            print_traceback()


def _escape_ansi(line: str) -> str:
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)


#
# The _BasePolicy and AnyThreadEventLoopPolicy below are borrowed from Tornado.
# Ref: https://www.tornadoweb.org/en/stable/_modules/tornado/platform/asyncio.html#AnyThreadEventLoopPolicy
#

if sys.platform == 'win32' and hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
    _BasePolicy = asyncio.WindowsSelectorEventLoopPolicy  # type: ignore
else:
    _BasePolicy = asyncio.DefaultEventLoopPolicy


class AnyThreadEventLoopPolicy(_BasePolicy):  # type: ignore
    """Event loop policy that allows loop creation on any thread.

    The default `asyncio` event loop policy only automatically creates
    event loops in the main threads. Other threads must create event
    loops explicitly or `asyncio.get_event_loop` (and therefore
    `.IOLoop.current`) will fail. Installing this policy allows event
    loops to be created automatically on any thread.

    Usage::
        asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
    """

    def get_event_loop(self) -> asyncio.AbstractEventLoop:
        try:
            return super().get_event_loop()
        except RuntimeError:
            # "There is no current event loop in thread %r"
            loop = self.new_event_loop()
            self.set_event_loop(loop)
            return loop
