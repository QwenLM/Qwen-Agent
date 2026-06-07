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

import builtins

import pytest

from qwen_agent.tools.python_executor import DateRuntime
from qwen_agent.utils.utils import save_audio_to_file


def _block_imports(monkeypatch, *blocked_modules):
    original_import = builtins.__import__

    def import_without_optional_dep(name, globals=None, locals=None, fromlist=(), level=0):
        if any(name == module or name.startswith(f'{module}.') for module in blocked_modules):
            raise ImportError(f'No module named {name}')
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, '__import__', import_without_optional_dep)


def test_date_runtime_reports_python_executor_extra_when_dateutil_missing(monkeypatch):
    _block_imports(monkeypatch, 'dateutil')

    with pytest.raises(ImportError, match=r'qwen-agent\[python_executor\]'):
        DateRuntime()


@pytest.mark.parametrize('missing_module', ['numpy', 'soundfile'])
def test_save_audio_to_file_reports_audio_dependencies_when_optional_dep_missing(monkeypatch, tmp_path, missing_module):
    _block_imports(monkeypatch, missing_module)

    with pytest.raises(ImportError, match='Saving audio content requires numpy and soundfile'):
        save_audio_to_file('', str(tmp_path / 'audio.wav'))
