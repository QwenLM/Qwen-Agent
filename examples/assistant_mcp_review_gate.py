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

"""An assistant that gets an independent, recomputable second opinion via a remote MCP server
before an irreversible action (a commit, a shell command, a trade, an on-chain transaction).

Demonstrates connecting Qwen-Agent to a REMOTE streamable-http MCP server (as opposed to the
local stdio server in assistant_mcp_sqlite_bot.py) using the "type": "streamable-http" config
plus a Bearer token in "headers" -- both already supported by MCPManager.

The remote server here is invinoveritas (https://api.babyblueviper.com) -- free registration at
/register returns an api_key with a few free trial calls per tool; no crypto/payment setup is
needed to try this example. The `review` tool returns a structured verdict + ranked issues; a
"reject" or "approve_with_concerns" verdict is a signal the agent should not proceed unmodified.
"""

import os
from typing import Optional

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI


def init_agent_service():
    llm_cfg = {'model': 'qwen-max'}
    system = (
        'You are a careful engineering assistant. Before recommending or taking any action that '
        'is costly or hard to reverse (a git commit, a shell command, a config change, a trade, '
        'an on-chain transaction), call the invinoveritas `review` tool on the exact artifact '
        'first and report its verdict to the user before proceeding. Treat a "reject" verdict as '
        'a blocker and a "approve_with_concerns" verdict as something to resolve, not ignore.'
    )
    tools = [{
        "mcpServers": {
            "invinoveritas": {
                "type": "streamable-http",
                "url": "https://api.babyblueviper.com/mcp",
                "headers": {
                    "Authorization": f"Bearer {os.environ['INVINOVERITAS_API_KEY']}"
                },
            }
        }
    }]
    bot = Assistant(
        llm=llm_cfg,
        name='Review-Gated Assistant',
        description='Gets an independent second opinion before irreversible actions',
        system_message=system,
        function_list=tools,
    )
    return bot


def test(query: str = (
    'Review this before I run it: `rm -rf /var/log/*.log && systemctl restart nginx`. '
    'Artifact type is a shell command.'
), file: Optional[str] = None):
    bot = init_agent_service()
    messages = []
    if not file:
        messages.append({'role': 'user', 'content': query})
    else:
        messages.append({'role': 'user', 'content': [{'text': query}, {'file': file}]})
    for response in bot.run(messages):
        print('bot response:', response)


def app_tui():
    bot = init_agent_service()
    messages = []
    while True:
        query = input('user question: ')
        if not query:
            print('user question cannot be empty!')
            continue
        messages.append({'role': 'user', 'content': query})
        response = []
        for response in bot.run(messages):
            print('bot response:', response)
        messages.extend(response)


def app_gui():
    bot = init_agent_service()
    chatbot_config = {
        'prompt.suggestions': [
            'Review this shell command before I run it: `rm -rf /var/log/*.log`',
            'Review this git diff before I commit it.',
            'Get a second opinion on this trade before I execute it.',
        ]
    }
    WebUI(bot, chatbot_config=chatbot_config).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
