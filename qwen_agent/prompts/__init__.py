"""
    Prompts are special agents: Using a prompt template to complete one QA.

"""
from .continue_writing import ContinueWriting
from .expand_writing import ExpandWriting
from .function_calling import FunctionCalling
from .gen_keyword import GenKeyword
from .outline_writing import OutlineWriting
from .react import ReAct
from .react_chat import ReActChat
from .retrieval_qa import RetrievalQA
from .role_play import RolePlay
from .summarize import Summarize
from .write_from_scratch import WriteFromScratch

DEFAULT_SYSTEM = 'You are a helpful assistant.'

__all__ = [
    'RetrievalQA', 'ContinueWriting', 'OutlineWriting', 'ExpandWriting',
    'ReAct', 'WriteFromScratch', 'Summarize', 'GenKeyword', 'RolePlay',
    'FunctionCalling', 'ReActChat'
]
