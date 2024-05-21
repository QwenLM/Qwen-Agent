from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import Message
from qwen_agent.tools import BaseTool
from qwen_agent.utils.utils import has_chinese_chars


class GroupChatAutoRouter(Agent):
    PROMPT_TEMPLATE_ZH = '''你扮演角色扮演游戏的上帝，你的任务是选择合适的发言角色。有如下角色：
{agent_descs}

角色间的对话历史格式如下，越新的对话越重要：
角色名: 说话内容

请阅读对话历史，并选择下一个合适的发言角色，从 [{agent_names}] 里选，当真实用户最近表明了停止聊天时，或话题应该终止时，请返回“[STOP]”，用户很懒，非必要不要选真实用户。
仅返回角色名或“[STOP]”，不要返回其余内容。'''

    PROMPT_TEMPLATE_EN = '''You are in a role play game. The following roles are available:
{agent_descs}

The format of dialogue history between roles is as follows:
Role Name: Speech Content

Please read the dialogue history and choose the next suitable role to speak.
When the user indicates to stop chatting or when the topic should be terminated, please return '[STOP]'.
Only return the role name from [{agent_names}] or '[STOP]'. Do not reply any other content.'''

    PROMPT_TEMPLATE = {
        'zh': PROMPT_TEMPLATE_ZH,
        'en': PROMPT_TEMPLATE_EN,
    }

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 agents: List[Agent] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 **kwargs):
        # This agent need prepend special system message according to inputted agents
        agent_descs = '\n'.join([f'{x.name}: {x.description}' for x in agents])
        lang = 'en'
        if has_chinese_chars(agent_descs):
            lang = 'zh'
        system_prompt = self.PROMPT_TEMPLATE[lang].format(agent_descs=agent_descs,
                                                          agent_names=', '.join([x.name for x in agents]))

        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_prompt,
                         name=name,
                         description=description,
                         **kwargs)

    def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]:

        dialogue = []
        for msg in messages:
            if msg.role == 'function' or not msg.content:
                continue
            if isinstance(msg.content, list):
                content = '\n'.join([x.text if x.text else '' for x in msg.content]).strip()
            else:
                content = msg.content.strip()
            display_name = msg.role
            if msg.name:
                display_name = msg.name
            if dialogue and dialogue[-1].startswith(display_name):
                dialogue[-1] += f'\n{content}'
            else:
                dialogue.append(f'{display_name}: {content}')

        if not dialogue:
            dialogue.append('对话刚开始，请任意选择一个发言人，别选真实用户')
        new_messages = [Message('user', '\n'.join(dialogue))]

        return self._call_llm(messages=new_messages)
