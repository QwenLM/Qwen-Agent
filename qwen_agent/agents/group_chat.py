import copy
import random
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.agents.assistant import Assistant
from qwen_agent.agents.group_chat_auto_router import GroupChatAutoRouter
from qwen_agent.agents.user_agent import PENDING_USER_INPUT, UserAgent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import Message
from qwen_agent.log import logger


class GroupChat(Agent):

    _VALID_AGENT_SELECTION_METHODS = [
        'manual', 'round_robin', 'random', 'auto'
    ]

    def __init__(self,
                 agents: Union[List[Agent], Dict],
                 max_round: Optional[int] = 3,
                 agent_selection_method: Optional[str] = 'auto',
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 **kwargs):
        super().__init__(**kwargs)
        assert agent_selection_method in self._VALID_AGENT_SELECTION_METHODS, f'You must choose agent_selection_method from {", ".join(self._VALID_AGENT_SELECTION_METHODS)}'
        self.agent_selection_method = agent_selection_method
        self.max_round = max_round

        if isinstance(agents, dict):
            self.agents = self._init_agents_from_config(agents, llm=llm)
        else:
            self.agents = agents
        assert len(self.agents) > 0
        if self.agent_selection_method == 'auto':
            assert llm is not None, 'Need to provide LLM to the host in auto mode'
            self.host = GroupChatAutoRouter(function_list=function_list,
                                            llm=llm,
                                            agents=self.agents,
                                            name='host')

    def _run(self,
             messages: List[Message] = None,
             lang: str = 'zh',
             need_batch_response: bool = True,
             mentioned_agents_name: List[str] = None,
             **kwargs) -> Iterator[List[Message]]:

        messages = copy.deepcopy(messages)
        for message in messages:
            if message.role == 'assistant':
                assert message.name, 'In group chat, each agent must be given a name'
            # name will be used for router
            # Todo: Dealing with situations where there are no real players
            if not message.name:
                message.name = message.role

        if need_batch_response:
            return self._gen_batch_response(
                messages=messages,
                lang=lang,
                mentioned_agents_name=mentioned_agents_name,
                **kwargs)
        else:
            return self._gen_one_response(
                messages=messages,
                lang=lang,
                mentioned_agents_name=mentioned_agents_name,
                **kwargs)

    def _gen_batch_response(self,
                            messages: List[Message] = None,
                            lang: str = 'zh',
                            mentioned_agents_name: List[str] = None,
                            **kwargs) -> Iterator[List[Message]]:
        # record all mentioned agents: reply in order
        mentioned_agents_name = mentioned_agents_name or []
        messages = copy.deepcopy(messages)

        response = []
        for i in range(self.max_round):
            if isinstance(messages[-1].content, list):
                content = '\n'.join([
                    x.text if x.text else '' for x in messages[-1].content
                ]).strip()
            else:
                content = messages[-1].content.strip()
            if '@' in content:
                for x in content.split('@'):
                    for agent in self.agents:
                        if x.startswith(agent.name):
                            if agent not in mentioned_agents_name:
                                mentioned_agents_name.append(agent.name)
                            break
            rsp = []
            for rsp in self._gen_one_response(
                    messages=messages,
                    lang=lang,
                    mentioned_agents_name=mentioned_agents_name,
                    **kwargs):
                yield response + rsp
            if not rsp:
                # The topic ends
                break
            if mentioned_agents_name:
                assert rsp[-1].name == mentioned_agents_name[0]
                mentioned_agents_name.pop(0)

            response += rsp
            if rsp[-1].content == PENDING_USER_INPUT:
                # Terminate group chat and wait for user input
                break
            messages.extend(rsp)
        yield response

    def _gen_one_response(self,
                          messages: List[Message] = None,
                          lang: str = 'zh',
                          mentioned_agents_name: List[str] = None,
                          **kwargs) -> Iterator[List[Message]]:

        selected_agent = self._select_agent(messages, mentioned_agents_name,
                                            lang)
        if selected_agent:
            logger.info(f'selected_agent_name: {selected_agent.name}')
            new_messages = self._manage_messages(messages, selected_agent.name)
            for rsp in selected_agent.run(messages=new_messages, **kwargs):
                yield rsp
        else:
            yield []

    def _select_agent(self,
                      messages: List[Message],
                      mentioned_agents_name: List[str] = None,
                      lang: str = 'zh') -> Union[Agent, None]:
        agents_map = {x.name: x for x in self.agents}
        if mentioned_agents_name:
            # manually select agent
            return agents_map[mentioned_agents_name[0]]

        if self.agent_selection_method == 'auto':
            *_, last = self.host.run(messages=messages, lang=lang)
            auto_selected_agent = None
            if isinstance(last[-1]['content'], str):
                auto_selected_agent = last[-1]['content']
            else:
                assert isinstance(last[-1]['content'], list)
                if 'text' in last[-1]['content'][0]:
                    auto_selected_agent = last[-1]['content'][0]['text']
            if auto_selected_agent in agents_map.keys():
                return agents_map[auto_selected_agent]
            elif auto_selected_agent == '[STOP]':
                return None

        if self.agent_selection_method == 'random':
            agent = random.choice(list(self.agents))
            return agent

        if self.agent_selection_method == 'manual':
            for i in range(3):
                agent_key = input('Please enter the selected agent name: ')
                if agent_key in agents_map.keys():
                    return agents_map[agent_key]
                else:
                    logger.warning(
                        f'Please select one agent from {str(list(agents_map.keys()))}'
                    )

        # round_robin
        if messages:
            agents_list = [x.name for x in self.agents]
            try:
                last_agent_index = agents_list.index(messages[-1]['name'])
            except ValueError:
                last_agent_index = -1
        else:
            last_agent_index = -1
        return self.agents[(last_agent_index + 1) % len(self.agents)]

    def _manage_messages(self, messages: List[Message],
                         name: str) -> List[Message]:
        new_messages = []
        new_msg = None
        i = 0
        while i < len(messages):
            msg = messages[i]
            if msg.name == name:
                if new_msg:
                    # have 'user' before 'assistant'
                    new_messages.append(new_msg)
                if not msg.function_call and (  # noqa
                    (not new_messages) or
                    (new_messages[-1].name == name)):  # noqa
                    new_messages.append(Message('user', f'{name}: '))

                new_msg = copy.deepcopy(msg)
                new_msg.role = 'assistant'
                new_messages.append(new_msg)
                new_msg = None
                if msg.function_call:
                    # append the function call msg
                    assert messages[i + 1].role == 'function'
                    new_messages.append(copy.deepcopy(messages[i + 1]))
                    i += 1
            else:
                if isinstance(msg.content, list):
                    content = '\n'.join([
                        x.text if x.text else '' for x in msg.content
                    ]).strip()
                else:
                    content = msg.content.strip()

                if content.strip():
                    if not new_msg:
                        new_msg = Message('user',
                                          f'{msg.name}: {content.strip()}')
                    else:
                        new_msg.content += f'\n{msg.name}: {content.strip()}'

                if msg.function_call:
                    # skip the function call msg
                    assert messages[i + 1].role == 'function'
                    assert messages[i + 2].role == 'assistant' and messages[
                        i + 2].name == msg.name
                    i += 1

            i += 1
        if new_msg:
            new_messages.append(new_msg)

        if new_messages and new_messages[-1].role == 'user':
            # This suffix will cause the host to always choose the same speaker
            new_messages[-1].content += f'\n{name}: '
            # pass
        else:
            new_messages.append(Message('user', f'{name}: '))
        return new_messages

    def _init_agents_from_config(
            self,
            cfgs: Dict,
            llm: Optional[Union[Dict, BaseChatModel]] = None) -> List[Agent]:

        def _build_system_from_role_config(config: Dict):
            role_chat_prompt = """你是{name}。{description}\n\n{instructions}"""

            name = config.get('name', '').strip()
            description = config.get('description', '').lstrip('\n').rstrip()
            instructions = config.get('instructions', '').lstrip('\n').rstrip()
            if len(instructions) >= len(description):
                description = ''  # redundant, as we already have instructions
            else:
                description = f'你的简介是：{description}'
            prompt = role_chat_prompt.format(name=name,
                                             description=description,
                                             instructions=instructions)

            knowledge_files = config.get('knowledge_files', [])
            selected_tools = config.get('selected_tools', [])
            return prompt, knowledge_files, selected_tools

        agents = []
        groupchat_background = '你在一个群聊中，'
        if cfgs.get('background', ''):
            groupchat_background += f'群聊背景为：{cfgs["background"]}'

        for cfg in cfgs['agents']:
            system, knowledge_files, selected_tools = _build_system_from_role_config(
                cfg)
            if 'is_human' in cfg and cfg['is_human']:
                # append human agent
                agents.append(
                    UserAgent(name=cfg['name'],
                              description=cfg['description']))
            else:
                # create npc agent by config
                other_agents = []
                for x in cfgs['agents']:
                    if x['name'] != cfg['name']:
                        other_agents.append(x['name'])
                agents.append(
                    Assistant(
                        llm=llm,
                        system_message=groupchat_background + system +
                        f'\n\n群里其他成员包括：{", ".join(other_agents)}，如果你想和别人对话，可以@成员名字。\n'
                        +
                        '\n\n讲话时请直接输出内容，不要输出你的名字。\n\n其他群友的发言历史以如下格式展示：\n角色名: 说话内容',
                        files=knowledge_files,
                        function_list=selected_tools,
                        name=cfg['name'],
                        description=cfg['description']))
        return agents
