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

import copy
import json
from typing import Dict, Iterator, List, Optional, Tuple, Union

import json5

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import Message
from qwen_agent.tools import BaseTool

CONFIG_SCHEMA = {
    'name': '... # 角色名字，5字左右',
    'description': '... # 角色简介，10字左右',
    'instructions': '... # 对角色的具体功能要求，30字左右，以第二人称称呼角色'
}

CONFIG_EXAMPLE = {
    'name': '小红书写作专家',
    'description': '我会写小红书爆款',
    'instructions': '你是小红书爆款写作专家，创作会先产5个标题（含emoji），再产正文（每段落含emoji，文末有tag）。'
}

BACKGROUND_TOKEN = '<Background>'
CONFIG_TOKEN = '<Config>'
ANSWER_TOKEN = '<Answer>'

ROLE_CREATE_SYSTEM = '''你扮演创建群聊的助手，请你根据用户输入的聊天主题，创建n个合适的虚拟角色，这些角色将在一个聊天室内对话，你需要和用户进行对话，明确用户对这些角色的要求。

配置文件为json格式：
{config_schema}

一个优秀的RichConfig样例如下：
{config_example}

在接下来的对话中，请在回答时严格使用如下格式，先生成群聊背景，然后依次生成所有角色的配置文件，最后再作出回复，除此之外不要回复其他任何内容：
{background_token}: ... # 生成的群聊背景，包括人物关系，预设故事背景等信息。
{config_token}: ... # 生成的第一个角色的配置文件，严格按照以上json格式，禁止为空。保证name和description不为空。instructions内容比description具体，如果用户给出了详细指令，请完全保留，用第二人称描述角色，例如“你是xxx，你具有xxx能力。
{config_token}: ... # 生成的第二个角色的配置文件，要求同上。
...
{config_token}: ... # 生成的第n个角色的配置文件，要求同上，如果用户没有明确指出n的数量，则n等于3；要求每个角色的名字不相同。
{answer_token}: ... # 你希望对用户说的话，用于询问用户对角色的要求，禁止为空，问题要广泛，不要重复问类似的问题。

如果群聊背景或某个角色的配置文件不需要更新，可以不重复输出{background_token}和对应的{config_token}的内容、只输出{answer_token}和需要修改的{config_token}的内容。'''.format(
    config_schema=json.dumps(CONFIG_SCHEMA, ensure_ascii=False, indent=2),
    config_example=json.dumps(CONFIG_EXAMPLE, ensure_ascii=False, indent=2),
    background_token=BACKGROUND_TOKEN,
    config_token=CONFIG_TOKEN,
    answer_token=ANSWER_TOKEN,
)
assert CONFIG_TOKEN in ROLE_CREATE_SYSTEM
assert ANSWER_TOKEN in ROLE_CREATE_SYSTEM


class GroupChatCreator(Agent):

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 **kwargs):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=ROLE_CREATE_SYSTEM,
                         name=name,
                         description=description,
                         **kwargs)

    def _run(self,
             messages: List[Message],
             agents: List[Agent] = None,
             lang: str = 'en',
             **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)
        messages = self._preprocess_messages(messages)

        for rsp in self._call_llm(messages=messages):
            yield self._postprocess_messages(rsp)

    def _preprocess_messages(self, messages: List[Message]) -> List[Message]:
        new_messages = []
        content = []
        for message in messages:
            if message.role != 'assistant':
                new_messages.append(message)
            else:
                if message.name == 'background':
                    content.append(f'{BACKGROUND_TOKEN}: {message.content}')
                elif message.name == 'role_config':
                    content.append(f'{CONFIG_TOKEN}: {message.content}')
                else:
                    content.append(f'{ANSWER_TOKEN}: {message.content}')
                    assert new_messages[-1].role == 'user'
                    new_messages.append(Message('assistant', '\n'.join(content)))
                    content = []
        return new_messages

    def _postprocess_messages(self, messages: List[Message]) -> List[Message]:
        new_messages = []
        assert len(messages) == 1
        message = messages[-1]
        background, cfgs, answer = self._extract_role_config_and_answer(message.content)
        if background:
            new_messages.append(Message(message.role, background, name='background'))
        if cfgs:
            for cfg in cfgs:
                new_messages.append(Message(message.role, cfg, name='role_config'))

        new_messages.append(Message(message.role, answer, name=message.name))
        return new_messages

    def _extract_role_config_and_answer(self, text: str) -> Tuple[str, List[str], str]:
        background, cfgs, answer = '', [], ''
        back_pos, cfg_pos, ans_pos = text.find(f'{BACKGROUND_TOKEN}: '), text.find(f'{CONFIG_TOKEN}: '), text.find(
            f'{ANSWER_TOKEN}: ')

        if ans_pos > -1:
            answer = text[ans_pos + len(f'{ANSWER_TOKEN}: '):]
        else:
            ans_pos = len(text)

        if back_pos > -1:
            if cfg_pos > back_pos:
                background = text[back_pos + len(f'{BACKGROUND_TOKEN}: '):cfg_pos]
            else:
                background = text[back_pos + len(f'{BACKGROUND_TOKEN}: '):ans_pos]
        text = text[:ans_pos]

        tmp = text.split(f'{CONFIG_TOKEN}: ')
        for t in tmp:
            if t.strip():
                try:
                    _ = json5.loads(t.strip())
                    cfgs.append(t.strip())
                except Exception:
                    continue

        if not (background or cfgs or answer):
            # There should always be ANSWER_TOKEN, if not, treat the entire content as answer
            answer = text
        return background, cfgs, answer
