import os
from pathlib import Path

""" ===== global setting ===== """
# the path of browser infomation
work_space_root = os.path.join(Path(__file__).resolve().parent.parent.parent, 'workspace/')
cache_root = os.path.join(work_space_root, 'browser_cache/')
download_root = os.path.join(work_space_root, 'download/')
browser_cache_file = 'browse.jsonl'
url_file = 'popup_url.jsonl'
# the path of workspace of code interpreter
code_interpreter_ws = os.path.join(work_space_root, 'ci_workspace/')

MAX_TOKEN = 4000  # the max token number of reference material
llm = 'Qwen-7B-Chat'  # ['Qwen-7B-Chat', 'gpt-4'] - the llm for using
prompt_lan = 'EN'  # ['CN', 'EN'] - the language of built-in prompt

# using similarity search on reference material before answer
similarity_search = True  # [True, False]
similarity_search_type = 'keyword'  # ['keyword', 'querymatch', 'llm']


""" ===== main.py setting ===== """
# the host and port of main.py
fast_api_host = '127.0.0.1'
fast_api_port = 8000
fast_api_figure_url = 'http://'+fast_api_host+':'+str(fast_api_port)+'/static'

pre_gen_question = False  # [True, False] - pre gen qustion for each block

""" ===== app.py setting (editing workstation) ===== """
# the host and port of editing workstation
app_host = '127.0.0.1'
app_port = 7864

max_days = 7  # the number of days for displaying
auto_agent = False  # [True, False] - automatic using plug-in after wrinting every section

# special instructions in editing
plugin_flag = '/plug'  # using plug-in
code_flag = '/code'  # using code interpreter
title_flag = '/title'  # writing a full article with planning


""" ===== app_in_browser.py setting (browser interactive interfaces) ===== """
app_in_browser_host = '127.0.0.1'
app_in_browser_port = 7863
