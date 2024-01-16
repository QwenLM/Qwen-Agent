"""
    Prompts are special agents: Using a prompt template to complete one QA.

"""

from .continue_writing import ContinueWriting
from .doc_qa import DocQA
from .expand_writing import ExpandWriting
from .gen_keyword import GenKeyword
from .outline_writing import OutlineWriting
from .write_from_scratch import WriteFromScratch

DEFAULT_SYSTEM = 'You are a helpful assistant.'

__all__ = [
    'DocQA', 'ContinueWriting', 'OutlineWriting', 'ExpandWriting',
    'WriteFromScratch', 'GenKeyword'
]
