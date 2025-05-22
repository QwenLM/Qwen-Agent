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

try:
    import gradio as gr
    assert gr.__version__ >= '5.0'
    import modelscope_studio.components.base as ms  # noqa
    import modelscope_studio.components.legacy as mgr  # noqa
except Exception as e:
    raise ImportError('The dependencies for GUI support are not installed. '
                      'Please install the required dependencies by running: pip install "qwen-agent[gui]"') from e
