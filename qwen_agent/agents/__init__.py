from qwen_agent.agent import Agent
from qwen_agent.multi_agent_hub import MultiAgentHub

from .article_agent import ArticleAgent
from .assistant import Assistant
# DocQAAgent is the default solution for long document question answering.
# The actual implementation of DocQAAgent may change with every release.
from .doc_qa.basic_doc_qa import BasicDocQA as DocQAAgent
from .fncall_agent import FnCallAgent
from .group_chat import GroupChat
from .group_chat_auto_router import GroupChatAutoRouter
from .group_chat_creator import GroupChatCreator
from .react_chat import ReActChat
from .router import Router
from .user_agent import UserAgent
from .write_from_scratch import WriteFromScratch

__all__ = [
    'Agent',
    'MultiAgentHub',
    'DocQAAgent',
    'Assistant',
    'ArticleAgent',
    'ReActChat',
    'Router',
    'UserAgent',
    'GroupChat',
    'WriteFromScratch',
    'GroupChatCreator',
    'GroupChatAutoRouter',
    'FnCallAgent',
]
