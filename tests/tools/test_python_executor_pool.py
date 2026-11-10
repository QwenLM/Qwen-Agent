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

"""`PythonExecutor` must not spawn worker processes that it never uses.

`PythonExecutor.__init__` used to build `multiprocess.Pool(cpu_count())`, but no
code path ever touched that pool: `apply()`/`batch_apply()` dispatch through
`pebble.ProcessPool`. Every executor therefore left `cpu_count()` idle worker
processes alive for its whole lifetime, and they were never closed or joined.
"""

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip('multiprocess')
pytest.importorskip('pebble')
pytest.importorskip('timeout_decorator')
pytest.importorskip('dateutil')

REPO_ROOT = Path(__file__).resolve().parents[2]

# Runs in a fresh interpreter so that leaked workers never land in the pytest
# process itself, and so that `multiprocess.active_children()` is unambiguous.
_SPAWN_SCRIPT = """
import multiprocess

from qwen_agent.tools.python_executor import PythonExecutor

executors = [PythonExecutor({{}}) for _ in range({count})]
print('children', len(multiprocess.active_children()))
print('executors', len(executors))
"""


def _children_after_constructing(count: int) -> int:
    proc = subprocess.run([sys.executable, '-c', _SPAWN_SCRIPT.format(count=count)],
                          cwd=str(REPO_ROOT),
                          capture_output=True,
                          text=True,
                          timeout=300)
    assert proc.returncode == 0, proc.stderr
    for line in proc.stdout.splitlines():
        if line.startswith('children '):
            return int(line.split()[1])
    raise AssertionError(f'Unexpected output: {proc.stdout!r}')


def test_constructing_executor_spawns_no_worker_processes():
    assert _children_after_constructing(1) == 0


def test_constructing_several_executors_spawns_no_worker_processes():
    assert _children_after_constructing(3) == 0


def test_executor_schema_is_unchanged():
    from qwen_agent.tools.python_executor import PythonExecutor

    assert PythonExecutor.name == 'python_executor'
    assert PythonExecutor.parameters['required'] == ['code']
