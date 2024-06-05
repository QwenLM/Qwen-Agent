"""Prompts are special agents: using a prompt template to complete one QA."""

from .continue_writing import ContinueWriting
from .expand_writing import ExpandWriting
from .outline_writing import OutlineWriting

__all__ = [
    'ContinueWriting',
    'OutlineWriting',
    'ExpandWriting',
]
