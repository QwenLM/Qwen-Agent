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
"""Regression tests for the opt-in safety gate on the (un-sandboxed) PythonExecutor.

PythonExecutor runs model-generated Python in the host process and is not
sandboxed by design (the registration is commented out and it ships under the
opt-in ``python_executor`` extra). This adds two opt-in controls that default to
the historical behaviour:

* env kill-switch ``QWEN_AGENT_DISABLE_PYTHON_EXECUTOR=1`` enforced at the
  exec/eval sink (``GenericRuntime``), and
* a ``confirm_callback`` policy hook consulted in ``PythonExecutor.call``.

The "blocked" tests FAIL on the unpatched base (the code is exec/eval'd anyway)
and PASS once the gate refuses execution. The sink-level tests intentionally use
``GenericRuntime`` directly so they do not depend on the flaky multiprocess pool.
"""
import pytest

from qwen_agent.tools.python_executor import GenericRuntime

try:
    from qwen_agent.tools.python_executor import CodeExecutionNotAllowedError
    _HAS_GATE = True
except ImportError:
    CodeExecutionNotAllowedError = Exception
    _HAS_GATE = False

_needs_gate = pytest.mark.skipif(not _HAS_GATE, reason='gate not present (unpatched base)')


# --------------------------------------------------------------------------- #
# Sink-level kill-switch (GenericRuntime.exec_code / eval_code)
# --------------------------------------------------------------------------- #
def test_kill_switch_blocks_exec(monkeypatch):
    monkeypatch.setenv('QWEN_AGENT_DISABLE_PYTHON_EXECUTOR', '1')
    rt = GenericRuntime()
    # On base this exec runs and sets `pwned`; the gate must refuse it instead.
    with pytest.raises(Exception):
        rt.exec_code('pwned = 1')
    assert 'pwned' not in rt._global_vars, 'exec must not run when execution is disabled'


def test_kill_switch_blocks_eval(monkeypatch):
    monkeypatch.setenv('QWEN_AGENT_DISABLE_PYTHON_EXECUTOR', '1')
    rt = GenericRuntime()
    with pytest.raises(Exception):
        rt.eval_code('1 + 1')


@_needs_gate
def test_kill_switch_raises_typed_error(monkeypatch):
    monkeypatch.setenv('QWEN_AGENT_DISABLE_PYTHON_EXECUTOR', '1')
    rt = GenericRuntime()
    with pytest.raises(CodeExecutionNotAllowedError):
        rt.exec_code('x = 1')


def test_default_exec_still_works(monkeypatch):
    """No env / no callback -> behaviour is unchanged (no false positive)."""
    monkeypatch.delenv('QWEN_AGENT_DISABLE_PYTHON_EXECUTOR', raising=False)
    rt = GenericRuntime()
    rt.exec_code('answer = 6 * 7')
    assert rt.eval_code('answer') == 42


# --------------------------------------------------------------------------- #
# Tool-level confirm callback (PythonExecutor.call), run before the pool
# --------------------------------------------------------------------------- #
def _make_executor(cfg):
    pytest.importorskip('multiprocess')
    pytest.importorskip('pebble')
    pytest.importorskip('timeout_decorator')
    from qwen_agent.tools.python_executor import PythonExecutor
    return PythonExecutor(cfg)


@_needs_gate
def test_call_confirm_denied_blocks_before_pool():
    seen = {}

    def deny(code):
        seen['code'] = code
        return False

    tool = _make_executor({'confirm_callback': deny, 'get_answer_from_stdout': True})
    with pytest.raises(CodeExecutionNotAllowedError):
        tool.call('{"code": "print(6*7)"}')
    # The callback was consulted with the model code, and execution was refused.
    assert seen.get('code') == 'print(6*7)'


@_needs_gate
def test_call_disabled_env_blocks(monkeypatch):
    monkeypatch.setenv('QWEN_AGENT_DISABLE_PYTHON_EXECUTOR', '1')
    tool = _make_executor({'get_answer_from_stdout': True})
    with pytest.raises(CodeExecutionNotAllowedError):
        tool.call('{"code": "print(1)"}')


if __name__ == '__main__':
    import sys
    sys.exit(pytest.main([__file__, '-v']))
