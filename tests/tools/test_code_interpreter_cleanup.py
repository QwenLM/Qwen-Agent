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
"""Regression tests: `_start_kernel` must release the Docker container (and the
kernel client's channels, if started) on every failure after `docker run`.

Everything that touches Docker or Jupyter is mocked; no daemon is needed."""
import subprocess
from unittest.mock import patch

import jupyter_client
import pytest

from qwen_agent.tools import code_interpreter as ci
from qwen_agent.tools.code_interpreter import CodeInterpreter

FAKE_CID = 'deadbeefcafe'


def _fake_subprocess_run(cmd, *args, **kwargs):
    if cmd[:3] == ['docker', 'run', '-d']:
        return subprocess.CompletedProcess(cmd, 0, stdout=f'{FAKE_CID}\n', stderr='')
    if cmd[:3] == ['docker', 'ps', '-q']:
        return subprocess.CompletedProcess(cmd, 0, stdout=f'{FAKE_CID}\n', stderr='')
    if cmd[:2] == ['docker', 'logs']:
        return subprocess.CompletedProcess(cmd, 0, stdout='', stderr='')
    return subprocess.CompletedProcess(cmd, 0, stdout='', stderr='')


class _FakeKernelClient:
    """Stands in for jupyter_client.BlockingKernelClient; `fail_at` picks where to raise."""
    fail_at = None
    instances = []

    def __init__(self, connection_file=None):
        self.channels_alive = False
        self.stop_channels_calls = 0
        _FakeKernelClient.instances.append(self)

    def load_connection_file(self):
        if _FakeKernelClient.fail_at == 'load':
            raise OSError('injected: cannot read connection file')

    def start_channels(self):
        self.channels_alive = True

    def stop_channels(self):
        # like jupyter_client: safe to call whether or not channels are running
        self.stop_channels_calls += 1
        self.channels_alive = False

    def wait_for_ready(self, timeout=None):
        if _FakeKernelClient.fail_at == 'ready':
            raise RuntimeError('injected: kernel never became ready')


@pytest.fixture
def tool(tmp_path):
    t = object.__new__(CodeInterpreter)  # skip __init__: it probes for a Docker daemon
    t.cfg = {}
    t.work_dir = str(tmp_path)
    t.instance_id = 'test-instance'
    t.docker_image_name = 'code-interpreter:test'
    t.container_work_dir = '/workspace'
    _FakeKernelClient.instances.clear()
    _FakeKernelClient.fail_at = None
    with patch.object(ci.subprocess, 'run', _fake_subprocess_run), \
         patch.object(ci.time, 'sleep', lambda *_: None), \
         patch.object(ci.shutil, 'copy', lambda *_: None), \
         patch.object(ci.asyncio, 'set_event_loop_policy', lambda *_: None), \
         patch.object(jupyter_client, 'BlockingKernelClient', _FakeKernelClient), \
         patch.object(CodeInterpreter, '_build_docker_image', lambda self: None), \
         patch.object(CodeInterpreter, '_get_free_ports', lambda self, n: list(range(40000, 40000 + n))), \
         patch.object(CodeInterpreter, '_remove_container_quietly') as removed:
        t._removed = removed
        yield t


def test_success_path_returns_client_and_keeps_container(tool):
    kc, cid = tool._start_kernel('k')
    assert cid == FAKE_CID
    assert kc is _FakeKernelClient.instances[0] and kc.channels_alive
    tool._removed.assert_not_called()
    assert kc.stop_channels_calls == 0


def test_failure_before_channels_start_removes_container(tool):
    _FakeKernelClient.fail_at = 'load'
    with pytest.raises(OSError, match='injected'):
        tool._start_kernel('k')
    tool._removed.assert_called_once_with(FAKE_CID)
    assert not _FakeKernelClient.instances[0].channels_alive


def test_failure_after_channels_start_stops_channels_and_removes_container(tool):
    _FakeKernelClient.fail_at = 'ready'
    with pytest.raises(RuntimeError, match='Kernel failed to start'):
        tool._start_kernel('k')
    tool._removed.assert_called_once_with(FAKE_CID)
    kc = _FakeKernelClient.instances[0]
    assert kc.stop_channels_calls >= 1 and not kc.channels_alive


def test_docker_run_failure_removes_container(tool):

    def failing_run(cmd, *a, **k):
        if cmd[:3] == ['docker', 'run', '-d']:
            return subprocess.CompletedProcess(cmd, 125, stdout=f'{FAKE_CID}\n', stderr='port is already allocated')
        return _fake_subprocess_run(cmd, *a, **k)
    with patch.object(ci.subprocess, 'run', failing_run), \
         pytest.raises(RuntimeError, match='Failed to start Docker container'):
        tool._start_kernel('k')
    tool._removed.assert_called_once_with(FAKE_CID)
