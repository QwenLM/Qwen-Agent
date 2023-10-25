import os
from pathlib import Path

# ===== global setting =====

# the path of browser infomation
work_space_root = os.path.join(Path(__file__).parent.parent, 'workspace/')
cache_root = os.path.join(work_space_root, 'browser_cache/')
download_root = os.path.join(work_space_root, 'download/')
browser_cache_file = 'browse.jsonl'
url_file = 'popup_url.jsonl'
# the path of workspace of code interpreter
code_interpreter_ws = os.path.join(work_space_root, 'ci_workspace/')

# ===== database_server.py setting =====

# the port of database_server.py
fast_api_port = 7866

address_file = os.path.join(work_space_root, 'address_file.json')

# ===== workstation_server.py setting (editing workstation) ===== """

max_days = 7  # the number of days for displaying

# special instructions in editing
plugin_flag = '/plug'  # using plug-in
code_flag = '/code'  # using code interpreter
title_flag = '/title'  # writing a full article with planning

# ===== assistant_server.py setting (browser interactive interfaces) ===== """

app_in_browser_port = 7863
