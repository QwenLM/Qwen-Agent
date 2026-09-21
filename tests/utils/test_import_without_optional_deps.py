# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import sys
import textwrap

import pytest

# None of these are in install_requires; importing the base package must not need them.
_IMPORT_WITHOUT_OPTIONAL_DEPS = textwrap.dedent('''
    import sys
    for name in ('numpy', 'soundfile', 'tqdm', 'dateutil'):
        sys.modules[name] = None
    import qwen_agent
    from qwen_agent.agents import Assistant
    from qwen_agent.tools import PythonExecutor  # noqa: F401
    from qwen_agent.utils.utils import save_audio_to_file
    try:
        save_audio_to_file(base_64='', file_name='unused.wav')
    except ImportError as e:
        assert 'soundfile' in str(e), e
    else:
        raise AssertionError('save_audio_to_file should fail without numpy/soundfile')
    print('ok')
''')


def test_import_without_optional_deps():
    result = subprocess.run([sys.executable, '-c', _IMPORT_WITHOUT_OPTIONAL_DEPS], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'ok'


if __name__ == '__main__':
    pytest.main([__file__])
