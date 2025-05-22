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

"""Prompts are special agents: using a prompt template to complete one QA."""

from .continue_writing import ContinueWriting
from .expand_writing import ExpandWriting
from .outline_writing import OutlineWriting

__all__ = [
    'ContinueWriting',
    'OutlineWriting',
    'ExpandWriting',
]
