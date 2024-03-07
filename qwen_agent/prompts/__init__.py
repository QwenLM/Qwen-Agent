"""Prompts are special agents: using a prompt template to complete one QA."""

from .continue_writing import ContinueWriting
from .doc_qa import DocQA
from .expand_writing import ExpandWriting
from .gen_keyword import GenKeyword
from .outline_writing import OutlineWriting

__all__ = [
    'DocQA', 'ContinueWriting', 'OutlineWriting', 'ExpandWriting', 'GenKeyword'
]
