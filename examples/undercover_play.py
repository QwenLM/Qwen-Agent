import json
import re

from qwen_agent.agents import Assistant

# config
game_rule = """谁是卧底游戏规则如下：
在场3个人，两个人拿到相同的一个词语，他们属于好人阵营，剩下的1个人拿到与之相关的另一个词语。
每人每轮只能说一句话描述自己拿到的词语(不能直接说出来那个词语)，目的是不能让卧底发现，但要给好人阵营的同胞暗示。
每轮描述完毕，3人投票选出怀疑是卧底的那个人，不能投自己。得票数最多的人出局，如果存在两个人平票，本轮就无人出局。
"""

host = """
现在你扮演《谁是卧底》游戏主持人，引导游戏进行。

%s

游戏流程如下：
游戏开始后，主持人先向每位玩家发消息私聊词语，生成如下json格式的每条消息来模拟发消息的过程：
[{"id": "player1", "role": "好人", "word": "山峰"}]
[{"id": "player2", "role": "好人", "word": "山峰"}]
[{"id": "player3", "role": "卧底", "word": "雪山"}]
注意你可以替换词语和卧底顺序。

然后按照每位玩家顺序发言，一轮完整发言后主持人主持大家依次投票，组织投票的环节仅需回答【请开始投票】。
注意：由于本场比赛只有3个人参与，只需出局一人就游戏结束，如果出局的是卧底，则好人获胜，你需要回复【游戏结束，好人获胜】，反之则回复【游戏结束，卧底获胜】，并展示你分别给好人和卧底的词。
我们在真实的玩游戏，每个轮次的描述和投票都有玩家真实进行，请你按照步骤，不要模拟游戏进度！
""" % game_rule

role_npc = """
你扮演一个谁是卧底游戏的玩家

%s

你拿到的词语是{word},你是{role}身份。记住不要直接说出自己的身份和词语！
""" % game_rule

llm_config = {'model': 'qwen-max', 'model_server': 'dashscope'}

# init agents
agents = {
    'host': {
        'obj': Assistant(llm=llm_config, system_message=host),
        'messages': []
    },
    'player1': {},
    'player2': {},
    'player3': {}
}
global_info = '已知信息：'


# chat initialization
def init_game():
    agents['host']['messages'].append({'role': 'user', 'content': '开始游戏！'})

    for retry in range(3):
        try:
            *_, last = agents['host']['obj'].run(agents['host']['messages'])
            response = last[-1]['content']
            print(response)
            agents['host']['messages'].extend(last)

            # parse infomation of generated agent
            pattern = r'\[\{"id":\s*"[^"]*",\s*"role":\s*"[^"]*",\s*"word":\s*"[^"]*"\}\]'
            matches = re.findall(pattern, response)
            all_gen_agent = [json.loads(match) for match in matches]
            print(all_gen_agent)

            # init player agent
            for agent in all_gen_agent:
                agent = agent[0]
                agents[agent['id']] = {
                    'obj':
                    Assistant(llm=llm_config,
                              system_message=role_npc.format(
                                  word=agent['word'], role=agent['role'])),
                    'messages': []
                }
            break
        except Exception:
            continue


turn = 0
while True:
    turn += 1
    for id, agent in agents.items():
        print(id, '>')
        if id == 'host' and turn == 1:
            init_game()
            continue
        if id == 'player3':  # user input
            response = input()
            agents[id]['messages'].append({
                'role': 'assistant',
                'content': response
            })
        else:
            agents[id]['messages'].append({
                'role': 'user',
                'content': global_info
            })
            *_, last = agents[id]['obj'].run(agents[id]['messages'])
            response = last[-1]['content']
            print(response)
            agents[id]['messages'].extend(last)

        # Chat ended
        if id == 'host' and '游戏结束' in response:
            exit(1)

        # broadcast message
        global_info += f'\n第{str(turn)}轮发言中：{id} 说{response}\n'
