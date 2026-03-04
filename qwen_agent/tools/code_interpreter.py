# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
import threading
import time
import uuid
import socket

from pathlib import Path
from typing import Dict, List, Optional, Union

import json5

from qwen_agent.log import logger
from qwen_agent.tools.base import BaseToolWithFileAccess, register_tool
from qwen_agent.utils.utils import append_signal_handler, extract_code, has_chinese_chars, print_traceback


LAUNCH_KERNEL_PY = """
from ipykernel import kernelapp as app
app.launch_new_instance()
"""

INIT_CODE_FILE = str(Path(__file__).absolute().parent / 'resource' / 'code_interpreter_init_kernel.py')
ALIB_FONT_FILE = str(Path(__file__).absolute().parent / 'resource' / 'AlibabaPuHuiTi-3-45-Light.ttf')
DOCKER_IMAGE_FILE = str(Path(__file__).absolute().parent / 'resource' / 'code_interpreter_image.dockerfile')

_KERNEL_CLIENTS: dict = {}
_DOCKER_CONTAINERS: Dict[str, str] = {}


def _kill_kernels_and_containers(_sig_num=None, _frame=None):
    for v in _KERNEL_CLIENTS.values():
        v.shutdown()
    for k in list(_KERNEL_CLIENTS.keys()):
        del _KERNEL_CLIENTS[k]

    for container_id in _DOCKER_CONTAINERS.values():
        try:
            subprocess.run(['docker', 'stop', container_id], timeout=10, capture_output=True, encoding='utf-8', errors='replace')
            subprocess.run(['docker', 'rm', container_id], timeout=10, capture_output=True, encoding='utf-8', errors='replace')
        except Exception:
            print(f"WARNING: Failed to stop and remove the Docker container: {container_id}")
    for k in list(_DOCKER_CONTAINERS.keys()):
        del _DOCKER_CONTAINERS[k]


# Make sure all containers are terminated even if killed abnormally:
# If not running in the main thread, (for example run in streamlit)
# register a signal would cause a RuntimeError
if threading.current_thread() is threading.main_thread():
    atexit.register(_kill_kernels_and_containers)
    append_signal_handler(signal.SIGTERM, _kill_kernels_and_containers)
    append_signal_handler(signal.SIGINT, _kill_kernels_and_containers)


@register_tool('codeInterpreter')
class CodeInterpreter(BaseToolWithFileAccess):
    description = 'Python code sandbox, which can be used to execute Python code.'
    parameters = {
        'type': 'object',
        'properties': {
            'code': {
                'description': 'The python code.',
                'type': 'string',
            }
        },
        'required': ['code'],
    }

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.work_dir: str = os.getenv('M6_CODE_INTERPRETER_WORK_DIR', self.work_dir)
        self.work_dir: str = self.cfg.get('work_dir', self.work_dir)
        self.instance_id: str = str(uuid.uuid4())
        self.docker_image_name: str = 'code-interpreter:latest'
        self.container_work_dir = '/workspace'
        _check_docker_availability()
        _check_host_deps()

    @property
    def args_format(self) -> str:
        fmt = self.cfg.get('args_format')
        if fmt is None:
            if has_chinese_chars([self.name_for_human, self.name, self.description, self.parameters]):
                fmt = '此工具的输入应为Markdown代码块。'
            else:
                fmt = 'Enclose the code within triple backticks (`) at the beginning and end of the code.'
        return fmt

    def call(self, params: Union[str, dict], files: List[str] = None, timeout: Optional[int] = 30, **kwargs) -> str:
        super().call(params=params, files=files)  # copy remote files to work_dir

        try:
            params = json5.loads(params)
            code = params['code']
        except Exception:
            code = extract_code(params)

        if not code.strip():
            return ''

        kernel_id: str = f'{self.instance_id}_{os.getpid()}'
        if kernel_id in _KERNEL_CLIENTS:
            kc = _KERNEL_CLIENTS[kernel_id]
        else:
            kc, container_id = self._start_kernel(kernel_id)
            with open(INIT_CODE_FILE) as fin:
                start_code = fin.read()
                container_font_path = f'{self.container_work_dir}/{os.path.basename(ALIB_FONT_FILE)}'
                start_code = start_code.replace('{{M6_FONT_PATH}}', repr(container_font_path)[1:-1])
                start_code += '\n%xmode Minimal'
            logger.info(self._execute_code(kc, start_code))
            _KERNEL_CLIENTS[kernel_id] = kc
            _DOCKER_CONTAINERS[kernel_id] = container_id

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
        # Recycle the jupyter subprocess and Docker container:
        k: str = f'{self.instance_id}_{os.getpid()}'
        if k in _KERNEL_CLIENTS:
            _KERNEL_CLIENTS[k].shutdown()
            del _KERNEL_CLIENTS[k]
        if k in _DOCKER_CONTAINERS:
            container_id = _DOCKER_CONTAINERS[k]
            try:
                subprocess.run(['docker', 'stop', container_id], timeout=10, capture_output=True, encoding='utf-8', errors='replace')
                subprocess.run(['docker', 'rm', container_id], timeout=10, capture_output=True, encoding='utf-8', errors='replace')
            except Exception:
                pass
            del _DOCKER_CONTAINERS[k]

    def _build_docker_image(self):
        """Build Docker image from Dockerfile if not exists"""
        # Check if image already exists
        result = subprocess.run(
            ['docker', 'images', '-q', self.docker_image_name],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.stdout.strip():
            logger.info(f'Docker image {self.docker_image_name} already exists')
            return
                
        logger.info(f'Building Docker image {self.docker_image_name} from {DOCKER_IMAGE_FILE}')
        dockerfile_dir = os.path.dirname(os.path.abspath(DOCKER_IMAGE_FILE))
        
        build_process = subprocess.run(
            ['docker', 'build', '-t', self.docker_image_name, '-f', DOCKER_IMAGE_FILE, dockerfile_dir],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if build_process.returncode != 0:
            raise RuntimeError(f'Failed to build Docker image: {build_process.stderr}')
        
        logger.info(f'Successfully built Docker image {self.docker_image_name}')

    def _get_free_ports(self, n=5):
        ports = []
        sockets = []
        for _ in range(n):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('', 0))
            ports.append(s.getsockname()[1])
            sockets.append(s)
        for s in sockets:
            s.close()
        return ports

    def _start_kernel(self, kernel_id: str):
        self._build_docker_image()

        host_connection_file = os.path.join(self.work_dir, f'kernel_connection_file_{kernel_id}_host.json')
        container_connection_file = os.path.join(self.work_dir, f'kernel_connection_file_{kernel_id}_container.json')
        launch_kernel_script = os.path.join(self.work_dir, f'launch_kernel_{kernel_id}.py')

        for f in [host_connection_file, container_connection_file, launch_kernel_script]:
            if os.path.exists(f):
                logger.info(f'WARNING: {f} already exists')
                os.remove(f)

        os.makedirs(self.work_dir, exist_ok=True)
        with open(launch_kernel_script, 'w') as fout:
            fout.write(LAUNCH_KERNEL_PY)

        work_dir_font = os.path.join(self.work_dir, os.path.basename(ALIB_FONT_FILE))
        if not os.path.exists(work_dir_font):
            shutil.copy(ALIB_FONT_FILE, work_dir_font)

        # prepare host connection file 
        host_conn_data = {
            "ip": "127.0.0.1",
            "key": str(uuid.uuid4()),
            "transport": "tcp",
            "signature_scheme": "hmac-sha256",
            "kernel_name": ""
        }
        ports = self._get_free_ports(5)
        port_names = ['shell_port', 'iopub_port', 'stdin_port', 'hb_port', 'control_port']
        port_config = dict(zip(port_names, ports))
        host_conn_data.update(port_config)
        with open(host_connection_file, 'w') as f:
            json.dump(host_conn_data, f)

        # prepare container connection file 
        container_conn_data = host_conn_data.copy()
        container_conn_data["ip"] = "0.0.0.0"
        with open(container_connection_file, 'w') as f:
            json.dump(container_conn_data, f)

        # prepare Docker launch cmd
        docker_run_cmd = [
            'docker', 'run', '-d',
            '--name', f'code_interpreter_{kernel_id}',
            '-v', f'{os.path.abspath(self.work_dir)}:{self.container_work_dir}',
            '-w', self.container_work_dir,
        ]
        for p in ports:
            docker_run_cmd.extend(['-p', f'{p}:{p}'])

        docker_run_cmd.extend([
            self.docker_image_name,
            'python', f'{self.container_work_dir}/{os.path.basename(launch_kernel_script)}',
            '--IPKernelApp.connection_file',
            f'{self.container_work_dir}/{os.path.basename(container_connection_file)}',
            '--KernelApp.allow_remote_access=True',
            '--matplotlib=inline',
            '--quiet',
        ])
        
        # start Docker container
        result = subprocess.run(docker_run_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            raise RuntimeError(f'Failed to start Docker container: {result.stderr}')
        
        container_id = result.stdout.strip()
        logger.info(f"INFO: Docker container ID = {container_id}")

        max_wait = 30
        wait_interval = 0.5
        elapsed = 0
        while elapsed < max_wait:
            check_result = subprocess.run(
                ['docker', 'ps', '-q', '-f', f'id={container_id}'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if check_result.stdout.strip():
                logger.info("Container is running")
                break
            time.sleep(wait_interval)
            elapsed += wait_interval
        else:
            logs = subprocess.run(
                ['docker', 'logs', container_id],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            raise RuntimeError(f'Container failed to start properly. Logs:\n{logs.stdout}\n{logs.stderr}')

        time.sleep(2)

        # start local jupter client
        from jupyter_client import BlockingKernelClient

        kc = BlockingKernelClient(connection_file=host_connection_file)
        asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
        kc.load_connection_file()
        kc.start_channels()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                kc.wait_for_ready(timeout=10)
                logger.info("Kernel is ready")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Kernel not ready (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(2)
                else:
                    logs = subprocess.run(
                        ['docker', 'logs', container_id],
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace'
                    )
                    raise RuntimeError(f'Kernel failed to start: {e}\nContainer logs:\n{logs.stdout}\n{logs.stderr}')
        
        return kc, container_id

    def _execute_code(self, kc, code: str) -> str:
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

    def _serve_image(self, image_base64: str) -> str:
        import PIL.Image

        image_file = f'{uuid.uuid4()}.png'
        local_image_file = os.path.join(self.work_dir, image_file)

        png_bytes = base64.b64decode(image_base64)
        assert isinstance(png_bytes, bytes)
        bytes_io = io.BytesIO(png_bytes)
        PIL.Image.open(bytes_io).save(local_image_file, 'png')

        image_server_url = os.getenv('M6_CODE_INTERPRETER_STATIC_URL', '')
        if image_server_url:
            return f'{image_server_url}/{image_file}'
        return local_image_file


def _check_docker_availability():
    try:
        result = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode != 0:
            raise RuntimeError('Docker is not available')
        
        result = subprocess.run(
            ['docker', 'info'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode != 0:
            raise RuntimeError('Docker daemon is not running')
        
        logger.info('Docker is available and running')
    except FileNotFoundError:
        raise RuntimeError('Docker is not installed. Please install Docker first.')
    except subprocess.TimeoutExpired:
        raise RuntimeError('Docker command timed out. Please check Docker installation.')
    except Exception as e:
        raise RuntimeError(f'Failed to check Docker availability: {str(e)}')


def _check_host_deps():
    """Check if host has required dependencies to connect to Docker container kernel"""
    try:
        from jupyter_client import BlockingKernelClient  # noqa
        import PIL.Image  # noqa
    except ImportError as e:
        raise ImportError(
            'The dependencies for Code Interpreter support are not installed. '
            'Please install the required dependencies by running: pip install "qwen-agent[code_interpreter]"') from e


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
