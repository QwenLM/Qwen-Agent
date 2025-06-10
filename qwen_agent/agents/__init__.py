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

from qwen_agent.agent import Agent, BasicAgent
from qwen_agent.multi_agent_hub import MultiAgentHub

from .article_agent import ArticleAgent
from .assistant import Assistant
from .dialogue_retrieval_agent import DialogueRetrievalAgent
from .dialogue_simulator import DialogueSimulator
# DocQAAgent is the default solution for long document question answering.
# The actual implementation of DocQAAgent may change with every release.
from .doc_qa import BasicDocQA as DocQAAgent
from .doc_qa import ParallelDocQA
from .fncall_agent import FnCallAgent
from .group_chat import GroupChat
from .group_chat_auto_router import GroupChatAutoRouter
from .group_chat_creator import GroupChatCreator
from .human_simulator import HumanSimulator
from .react_chat import ReActChat
from .router import Router
from .tir_agent import TIRMathAgent
from .user_agent import UserAgent
from .virtual_memory_agent import VirtualMemoryAgent
from .write_from_scratch import WriteFromScratch

__all__ = [
    'Agent',
    'BasicAgent',
    'MultiAgentHub',
    'DocQAAgent',
    'DialogueSimulator',
    'HumanSimulator',
    'ParallelDocQA',
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
    'VirtualMemoryAgent',
    'DialogueRetrievalAgent',
    'TIRMathAgent',
]
