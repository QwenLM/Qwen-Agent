import json
import os
import shutil
from pathlib import Path

from qwen_agent.utils.utils import get_basename_from_url, hash_sha256
from qwen_server.schema import GlobalConfig
from qwen_server.utils import read_meta_data_by_condition


def test_database_server():
    server_config_path = Path(__file__).resolve().parent.parent.parent / 'qwen_server/server_config.json'
    with open(server_config_path, 'r') as f:
        server_config = json.load(f)
        server_config = GlobalConfig(**server_config)
    if os.path.exists('workspace'):
        shutil.rmtree('workspace')
    os.makedirs(server_config.path.work_space_root)
    os.makedirs(server_config.path.download_root)
    os.makedirs(server_config.path.code_interpreter_ws)

    # cache
    from qwen_server.database_server import cache_page, update_pop_url

    data = {
        'url':
            'https://github.com/QwenLM/Qwen-Agent',
        'content':
            '<p>Qwen-Agent is a framework for developing LLM applications based on the instruction following, tool usage, planning, and memory capabilities of Qwen. </p>'
    }
    cache_page(**data)

    new_url = os.path.join(server_config.path.download_root, hash_sha256(data['url']),
                           get_basename_from_url(data['url']))
    assert os.path.exists(new_url)

    meta_file = os.path.join(server_config.path.work_space_root, 'meta_data.jsonl')
    assert os.path.exists(meta_file)
    res = read_meta_data_by_condition(meta_file, url=new_url)
    assert isinstance(res, dict)
    assert res['url'] == new_url

    # pop up
    update_pop_url(new_url)
    cache_file_popup_url = os.path.join(server_config.path.work_space_root, 'popup_url.jsonl')
    assert os.path.exists(cache_file_popup_url)
