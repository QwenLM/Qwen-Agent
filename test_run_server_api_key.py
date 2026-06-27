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
"""Regression tests for issue #904: API keys must not be persisted to the
tracked config file or written to logs.

Place this file at the repository root and run:

    pip install -e .
    pytest test_run_server_api_key.py -v
"""
import json
import sys
from pathlib import Path

# Locate the repo root (the directory that contains run_server.py), whether
# this test sits at the root or under tests/.
REPO_ROOT = Path(__file__).resolve().parent
while not (REPO_ROOT / 'run_server.py').exists() and REPO_ROOT != REPO_ROOT.parent:
    REPO_ROOT = REPO_ROOT.parent
sys.path.insert(0, str(REPO_ROOT))

import run_server  # noqa: E402
from qwen_server.schema import GlobalConfig  # noqa: E402

SECRET = 'sk-supersecret-DO-NOT-LEAK-1234567890'


def _base_config():
    with open(REPO_ROOT / 'qwen_server' / 'server_config.json') as f:
        return GlobalConfig(**json.load(f))


class _Args:
    model_server = 'dashscope'
    api_key = SECRET
    llm = 'qwen-plus'
    server_host = '127.0.0.1'
    max_ref_token = 4000
    workstation_port = 7864


def test_api_key_not_written_to_config_file(tmp_path):
    out = tmp_path / 'server_config.json'
    run_server.update_config(_base_config(), _Args(), out)

    text = out.read_text()
    assert SECRET not in text, 'API key leaked into the persisted config file'
    assert json.loads(text)['server']['api_key'] == ''


def test_in_memory_config_still_has_key(tmp_path):
    # Functionality must be preserved: the running process keeps the real key.
    out = tmp_path / 'server_config.json'
    cfg = run_server.update_config(_base_config(), _Args(), out)
    assert cfg.server.api_key == SECRET


def test_log_output_is_redacted():
    cfg = _base_config()
    cfg.server.api_key = SECRET
    redacted = run_server.redact_secrets(cfg)
    assert redacted['server']['api_key'] == '***'
    assert SECRET not in json.dumps(redacted)


def test_provider_env_var_selection():
    assert run_server.api_key_env_var('dashscope') == 'DASHSCOPE_API_KEY'
    assert run_server.api_key_env_var('http://localhost:8000/v1') == 'OPENAI_API_KEY'
