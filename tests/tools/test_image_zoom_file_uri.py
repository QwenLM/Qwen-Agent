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

from pathlib import Path

import pytest
from PIL import Image

from qwen_agent.llm.schema import ContentItem, Message
from qwen_agent.tools.image_zoom_in_qwen3vl import ImageZoomInToolQwen3VL


@pytest.mark.parametrize('filename,use_uri', [('image with space.png', True), ('图片.png', True),
                                              ('image#100%.png', True), ('plain.png', False)])
def test_image_zoom_opens_local_images(tmp_path, filename, use_uri):
    source = tmp_path / filename
    Image.new('RGB', (64, 64), color='red').save(source)
    location = source.as_uri() if use_uri else str(source)
    tool = ImageZoomInToolQwen3VL({'work_dir': str(tmp_path / 'out')})

    result = tool.call(
        {
            'bbox_2d': [0, 0, 1000, 1000],
            'label': 'image',
            'img_idx': 0
        },
        messages=[Message(role='user', content=[ContentItem(image=location)])],
    )

    assert len(result) == 1
    assert result[0].image is not None, result
    output = Path(result[0].image)
    assert output.is_file()
    with Image.open(output) as image:
        assert image.getpixel((0, 0)) == (255, 0, 0)
