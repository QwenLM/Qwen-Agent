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

"""A chess play game implemented by group chat"""

from qwen_agent.agents import GroupChat
from qwen_agent.gui import WebUI
from qwen_agent.llm.schema import Message

# Define a configuration file for a multi-agent:
# one real player, one NPC player, and one chessboard
NPC_NAME = '小明'
USER_NAME = '小塘'
CFGS = {
    'background':
        f'一个五子棋群组，棋盘为5*5，黑棋玩家和白棋玩家交替下棋，每次玩家下棋后，棋盘进行更新并展示。{NPC_NAME}下白棋，{USER_NAME}下黑棋。',
    'agents': [
        {
            'name':
                '棋盘',
            'description':
                '负责更新棋盘',
            'instructions':
                '你扮演一个五子棋棋盘，你可以根据原始棋盘和玩家下棋的位置坐标，把新的棋盘用矩阵展示出来。棋盘中用0代表无棋子、用1表示黑棋、用-1表示白棋。用坐标<i,j>表示位置，i代表行，j代表列，棋盘左上角位置为<0,0>。',
            'selected_tools': ['code_interpreter'],
        },
        {
            'name':
                NPC_NAME,
            'description':
                '白棋玩家',
            'instructions':
                '你扮演一个玩五子棋的高手，你下白棋。棋盘中用0代表无棋子、用1黑棋、用-1白棋。用坐标<i,j>表示位置，i代表行，j代表列，棋盘左上角位置为<0,0>，请决定你要下在哪里，你可以随意下到一个位置，不要说你是AI助手不会下！返回格式为坐标：\n<i,j>\n除了这个坐标，不要返回其他任何内容',
        },
        {
            'name': USER_NAME,
            'description': '黑棋玩家',
            'is_human': True
        },
    ],
}


def test(query: str = '<1,1>'):
    bot = GroupChat(agents=CFGS, llm={'model': 'qwen-max'})

    messages = [Message('user', query, name=USER_NAME)]
    for response in bot.run(messages=messages):
        print('bot response:', response)


def app_tui():
    # Define a group chat agent from the CFGS
    bot = GroupChat(agents=CFGS, llm={'model': 'qwen-max'})
    # Chat
    messages = []
    while True:
        query = input('user question: ')
        messages.append(Message('user', query, name=USER_NAME))
        response = []
        for response in bot.run(messages=messages):
            print('bot response:', response)
        messages.extend(response)


def app_gui():
    # Define a group chat agent from the CFGS
    bot = GroupChat(agents=CFGS, llm={'model': 'qwen-max'})
    chatbot_config = {
        'user.name': '小塘',
        'prompt.suggestions': [
            '开始！我先手，落子 <1,1>',
            '我后手，请小明先开始',
            '新开一盘，我先开始',
        ],
        'verbose': True
    }

    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()


if __name__ == '__main__':
    # test()
    # app_tui()
    app_gui()
