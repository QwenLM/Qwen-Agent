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

import os

from PIL import Image

from qwen_agent.llm.schema import ContentItem, Message
from qwen_agent.tools.image_zoom_in_qwen3vl import ImageZoomInToolQwen3VL

IMG_WIDTH = 500
IMG_HEIGHT = 400


def _make_tool_and_messages(tmp_path) -> tuple:
    image_path = os.path.join(str(tmp_path), 'image.png')
    Image.new('RGB', (IMG_WIDTH, IMG_HEIGHT), (200, 30, 30)).save(image_path)
    tool = ImageZoomInToolQwen3VL({'work_dir': str(tmp_path)})
    messages = [Message(role='user', content=[ContentItem(image=image_path)])]
    return tool, messages


def test_maybe_resize_bbox_always_returns_a_valid_region(tmp_path):
    tool, _ = _make_tool_and_messages(tmp_path)
    bboxes = [
        (50, 40, 150, 120),  # normal bbox
        (-30, -20, 40, 30),  # partly outside the top-left corner
        (600, 400, 700, 520),  # completely outside the image
        (1200, 1000, 1400, 1300),  # pixel-scale coordinates of an 1000-normalised model
        (300, 300, 100, 100),  # inverted bbox
        (50, 80, 150, 80),  # zero height
        (200, 80, 200, 160),  # zero width
    ]
    for bbox in bboxes:
        left, top, right, bottom = tool.maybe_resize_bbox(*bbox, IMG_WIDTH, IMG_HEIGHT)
        assert 0 <= left < right <= IMG_WIDTH, f'invalid horizontal range for {bbox}: {(left, right)}'
        assert 0 <= top < bottom <= IMG_HEIGHT, f'invalid vertical range for {bbox}: {(top, bottom)}'


def test_zoom_in_with_out_of_range_bbox_returns_a_crop(tmp_path):
    tool, messages = _make_tool_and_messages(tmp_path)
    bboxes = [
        [1200, 1000, 1400, 1300],  # pixel-scale coordinates instead of 0-1000
        [100, 200, 300, 200],  # zero height
        [200, 100, 200, 300],  # zero width
        [300, 300, 100, 100],  # inverted bbox
    ]
    for bbox in bboxes:
        result = tool.call({'bbox_2d': bbox, 'label': 'region', 'img_idx': 0}, messages=messages)
        assert len(result) == 1
        item = result[0]
        assert item.image, f'expected a cropped image for {bbox}, but got: {item}'
        assert os.path.isfile(item.image)
        with Image.open(item.image) as cropped:
            assert cropped.width > 0 and cropped.height > 0
