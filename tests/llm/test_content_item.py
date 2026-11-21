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

import pytest

from qwen_agent.llm.schema import ContentItem, Message
from qwen_agent.utils.utils import format_as_multimodal_message


def test_empty_media_value_is_treated_as_not_provided():
    item = ContentItem(text='look at this', image='')
    assert item.type == 'text'
    assert item.value == 'look at this'
    assert item.model_dump() == {'text': 'look at this'}

    assert ContentItem(text='look at this', video=[]).type == 'text'
    assert ContentItem(text='look at this', audio={}).type == 'text'
    assert ContentItem(text='look at this', file='').type == 'text'


def test_item_with_only_an_empty_media_value_is_rejected():
    for kwargs in ({'image': ''}, {'video': []}, {'file': ''}):
        with pytest.raises(ValueError, match='Exactly one of'):
            ContentItem(**kwargs)


def test_multimodal_conversion_keeps_a_single_field():
    msg = Message(role='user', content=[ContentItem(text='look at this', image='')])
    converted = format_as_multimodal_message(msg,
                                             add_upload_info=True,
                                             add_multimodel_upload_info=True,
                                             add_audio_upload_info=True)
    assert converted.model_dump() == {'role': 'user', 'content': [{'text': 'look at this'}]}


def test_non_empty_media_value_is_unchanged():
    item = ContentItem(image='a.png')
    assert item.type == 'image'
    assert item.value == 'a.png'
    assert item.model_dump() == {'image': 'a.png'}


if __name__ == '__main__':
    test_empty_media_value_is_treated_as_not_provided()
    test_item_with_only_an_empty_media_value_is_rejected()
    test_multimodal_conversion_keeps_a_single_field()
    test_non_empty_media_value_is_unchanged()
