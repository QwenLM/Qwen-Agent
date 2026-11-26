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

import json
import multiprocessing
import os

import pytest

multiprocess = pytest.importorskip('multiprocess')
pytest.importorskip('pebble')
pytest.importorskip('timeout_decorator')
pytest.importorskip('dateutil.relativedelta')


@pytest.fixture
def make_executor(monkeypatch):
    from qwen_agent.tools.python_executor import PythonExecutor

    # Keep real process pools, with one worker so recovery happens within a batch.
    monkeypatch.setattr(multiprocess, 'cpu_count', lambda: 1)
    monkeypatch.setattr(os, 'cpu_count', lambda: 1)
    executors = []

    def create(cfg=None):
        executor = PythonExecutor({'timeout_length': 5, **(cfg or {})})
        executors.append(executor)
        return executor

    yield create

    for executor in executors:
        executor.pool.close()
        executor.pool.join()


@pytest.mark.parametrize('cfg, code, expected', [
    ({}, 'print(7)', '7'),
    ({
        'get_answer_from_stdout': False,
        'get_answer_symbol': 'answer'
    }, 'answer = 7', '7'),
    ({
        'get_answer_from_stdout': False,
        'get_answer_expr': 'answer + 1'
    }, 'answer = 6', '7'),
    ({
        'get_answer_from_stdout': False
    }, 'answer = 6\nanswer + 1', '7'),
])
def test_python_executor_answer_modes(make_executor, cfg, code, expected):
    assert make_executor(cfg).apply(code) == (expected, 'Done')


def test_python_executor_call(make_executor):
    assert make_executor().call(json.dumps({'code': 'print(7)'})) == ('7', 'Done')


def test_python_executor_batch_error_and_recovery(make_executor):
    results = make_executor().batch_apply(["print('first')", "raise ValueError('bad code')", "print('last')"])
    assert results[0] == ('first', 'Done')
    assert results[1] == ('', 'ValueError: bad code')
    assert results[2] == ('last', 'Done')


def test_python_executor_timeout_and_worker_cleanup(make_executor, tmp_path):
    # Leave time for a replacement worker to import the package on Windows.
    executor = make_executor({'timeout_length': 5})
    initial_children = {child.pid for child in multiprocessing.active_children()}
    pid_file = tmp_path / 'timed-worker.txt'
    code = ('import os\nfrom pathlib import Path\n'
            f"Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
            'while True:\n    pass')

    results = executor.batch_apply([code, "import os\nprint('recovered', os.getpid())"])

    assert results[0][0] == ''
    assert 'Timeout' in results[0][1]
    assert results[1][1] == 'Done'
    assert results[1][0].startswith('recovered ')
    if os.name == 'nt':
        # Windows relies on the pool deadline, which must replace the busy worker.
        assert int(pid_file.read_text()) != int(results[1][0].split()[1])
    assert {child.pid for child in multiprocessing.active_children()} <= initial_children


@pytest.mark.skipif(os.name == 'nt', reason='SIGALRM is only available on POSIX')
def test_python_executor_posix_signal_timeout():
    from qwen_agent.tools.python_executor import GenericRuntime, PythonExecutor

    result, report = PythonExecutor.execute(['while True:', '    pass'],
                                            get_answer_from_stdout=True,
                                            runtime=GenericRuntime(),
                                            timeout_length=1)
    assert result == ''
    assert 'Timeout' in report
