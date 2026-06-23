import json
from types import SimpleNamespace

from qwen_server.schema import GlobalConfig
from run_server import _redact_config, update_config


def _load_config():
    with open('qwen_server/server_config.json', 'r') as f:
        return GlobalConfig(**json.load(f))


def test_update_config_keeps_cli_api_key_out_of_tracked_config(tmp_path):
    server_config = _load_config()
    server_config.server.api_key = 'existing-file-key'
    tracked_config_path = tmp_path / 'server_config.json'
    runtime_config_path = tmp_path / 'workspace' / 'server_config.local.json'

    args = SimpleNamespace(
        model_server='https://model.example/v1',
        api_key='runtime-secret-key',
        llm='qwen-max',
        server_host='127.0.0.1',
        max_ref_token=1234,
        workstation_port=9001,
    )

    runtime_config = update_config(server_config, args, tracked_config_path, runtime_config_path)

    assert runtime_config.server.api_key == 'runtime-secret-key'

    tracked_config = json.loads(tracked_config_path.read_text())
    assert tracked_config['server']['api_key'] == 'existing-file-key'
    assert tracked_config['server']['api_key'] != 'runtime-secret-key'
    assert tracked_config['server']['model_server'] == 'https://model.example/v1'
    assert tracked_config['server']['llm'] == 'qwen-max'

    local_runtime_config = json.loads(runtime_config_path.read_text())
    assert local_runtime_config['server']['api_key'] == 'runtime-secret-key'
    assert local_runtime_config['server']['model_server'] == 'https://model.example/v1'


def test_update_config_uses_existing_api_key_when_cli_key_omitted(tmp_path):
    server_config = _load_config()
    server_config.server.api_key = 'existing-file-key'
    tracked_config_path = tmp_path / 'server_config.json'
    runtime_config_path = tmp_path / 'workspace' / 'server_config.local.json'

    args = SimpleNamespace(
        model_server='https://model.example/v1',
        api_key='',
        llm='qwen-max',
        server_host='127.0.0.1',
        max_ref_token=1234,
        workstation_port=9001,
    )

    runtime_config = update_config(server_config, args, tracked_config_path, runtime_config_path)

    assert runtime_config.server.api_key == 'existing-file-key'

    tracked_config = json.loads(tracked_config_path.read_text())
    assert tracked_config['server']['api_key'] == 'existing-file-key'

    local_runtime_config = json.loads(runtime_config_path.read_text())
    assert local_runtime_config['server']['api_key'] == 'existing-file-key'


def test_redact_config_masks_api_key():
    server_config = _load_config()
    server_config.server.api_key = 'runtime-secret-key'

    redacted = _redact_config(server_config)

    assert redacted['server']['api_key'] == '***'
    assert 'runtime-secret-key' not in json.dumps(redacted)
