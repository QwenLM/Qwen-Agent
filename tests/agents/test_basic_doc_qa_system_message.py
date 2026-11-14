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

"""BasicDocQA must keep a structured system message structured.

`BasicDocQA._run` appended the DocQA prompt with `messages[0][CONTENT] += ...`.
When the system message carries multimodal content (a `List[ContentItem]`), `+=`
extends the list with the *characters* of the prompt instead of adding one content
item: the prompt is destroyed, the list holds bare `str` items, and the request
fails in `format_as_multimodal_message` with
`AttributeError: 'str' object has no attribute 'get_type_and_value'`.
"""

from types import SimpleNamespace

from qwen_agent.agents import DocQAAgent
from qwen_agent.llm.oai import TextChatAtOAI
from qwen_agent.llm.schema import ContentItem, Message

DOC_QA_PROMPT_EN = ('Please fully understand the content of the following reference materials and organize a clear '
                    "response that meets the user's questions.\n# Reference materials:\n")


class _RecordingOAI(TextChatAtOAI):
    """OpenAI-compatible chat model that records the request it receives."""

    def __init__(self):
        super().__init__({'model': 'qwen2.5-7b-instruct', 'model_server': 'http://127.0.0.1:9/v1'})
        self.requests = []
        self._chat_complete_create = self._stub_create

    def _stub_create(self, *args, **kwargs):
        self.requests.append(kwargs.get('messages'))
        yield SimpleNamespace(choices=[
            SimpleNamespace(delta=SimpleNamespace(content='the answer', reasoning_content=None, tool_calls=None))
        ])


def test_structured_system_message_is_preserved(tmp_path, monkeypatch):
    # Keep the tool workspaces created by Memory/Storage out of the repository.
    monkeypatch.chdir(tmp_path)

    llm = _RecordingOAI()
    bot = DocQAAgent(llm=llm)

    responses = []
    for responses in bot.run([
            Message('system', [ContentItem(text='You are a careful assistant.')]),
            Message('user', 'What is the password policy?'),
    ]):
        pass

    assert llm.requests, 'the model was never called'
    system_content = llm.requests[0][0]['content']
    if isinstance(system_content, str):
        system_text = system_content
    else:
        # A text-only adapter may keep the multimodal format; every item must still be structured.
        assert all(isinstance(item, dict) and 'text' in item for item in system_content), system_content
        system_text = ''.join(item['text'] for item in system_content)

    assert system_text == 'You are a careful assistant.\n\n' + DOC_QA_PROMPT_EN
    assert responses[-1]['content'] == 'the answer'


def test_string_system_message_is_still_supported(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    llm = _RecordingOAI()
    bot = DocQAAgent(llm=llm)

    responses = []
    for responses in bot.run([
            {
                'role': 'system',
                'content': 'You are a careful assistant.'
            },
            {
                'role': 'user',
                'content': 'What is the password policy?'
            },
    ]):
        pass

    assert llm.requests, 'the model was never called'
    system_content = llm.requests[0][0]['content']
    assert system_content == 'You are a careful assistant.\n\n' + DOC_QA_PROMPT_EN
    assert responses[-1]['content'] == 'the answer'
