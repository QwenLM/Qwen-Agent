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

"""A security research assistant example using the ContrastAPI MCP server.

ContrastAPI exposes 33 cascade-aware security tools (CVE lookup with EPSS +
CISA KEV, MITRE CWE catalog, domain audit, IP threat report, dependency
scanner, IOC enrichment, ...) over a remote MCP server. Each response emits
``next_calls`` workflow hints so the agent chains related lookups
automatically (e.g. cve_lookup -> exploit_lookup -> kev_detail -> cwe_lookup).
Free tier: 100 credits/hour, no API key required.

Docs: https://api.contrastcyber.com
MCP manifest: https://api.contrastcyber.com/mcp.json
"""

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI


def init_agent_service():
    llm_cfg = {'model': 'qwen-max'}
    system = (
        '你是一名安全研究助手，可以调用 ContrastAPI 的工具来查询 CVE、'
        '审计域名、分析 IP 威胁情报、扫描依赖漏洞等。回答前请先调用相关工具，'
        '并在给出建议前检查返回结果中的 verdict.completeness 字段。'
    )
    tools = [{
        'mcpServers': {
            'contrastapi': {
                'command': 'npx',
                'args': ['-y', 'mcp-remote', 'https://api.contrastcyber.com/mcp/'],
            }
        }
    }]
    bot = Assistant(
        llm=llm_cfg,
        name='安全研究助手',
        description='CVE / 域名 / IP / 依赖漏洞查询',
        system_message=system,
        function_list=tools,
    )
    return bot


def test(query='CVE-2021-44228 是否正在被利用？请检查 EPSS 和 KEV。'):
    bot = init_agent_service()
    messages = [{'role': 'user', 'content': query}]
    for response in bot.run(messages):
        print('bot response:', response)


def app_tui():
    bot = init_agent_service()
    messages = []
    while True:
        query = input('user question: ')
        if not query:
            print('user question cannot be empty！')
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
            'CVE-2021-44228 是否正在被利用？请检查 EPSS 和 KEV。',
            '审计 example.com 的安全状况，包括 SSL、DNS、SPF/DMARC。',
            '查询 IP 8.8.8.8 的威胁情报（Shodan + AbuseIPDB + ASN）。',
            '扫描以下依赖是否存在已知漏洞：requests==2.25.0, flask==1.0.0',
        ]
    }
    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
