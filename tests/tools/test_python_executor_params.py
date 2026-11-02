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

import io
import json
from contextlib import redirect_stdout

import pytest

from qwen_agent.tools.python_executor import GenericRuntime, PythonExecutor


class LocalExecutor(PythonExecutor):
    """Exercise call's decoding without creating multiprocessing pools."""

    def __init__(self):
        self.runtime = GenericRuntime()

    def apply(self, code):
        output = io.StringIO()
        with redirect_stdout(output):
            self.runtime.exec_code(code)
        return [output.getvalue(), 'Done']


@pytest.mark.parametrize('params', [
    {
        'code': 'print(6 * 7)'
    },
    json.dumps({'code': 'print(6 * 7)'}),
    'print(6 * 7)',
    '```python\nprint(6 * 7)\n```',
])
def test_executor_decodes_supported_parameter_forms(params):
    assert LocalExecutor().call(params) == ['42\n', 'Done']


@pytest.mark.parametrize('params', [{'code': '   '}, json.dumps({'code': '   '})])
def test_executor_returns_empty_result_for_blank_code(params):
    assert LocalExecutor().call(params) == ['', '']
