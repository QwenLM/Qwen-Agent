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

import math
import os
import uuid
from io import BytesIO
from math import ceil, floor
from typing import List, Union

import requests
from PIL import Image

from qwen_agent.llm.schema import ContentItem
from qwen_agent.log import logger
from qwen_agent.tools.base import BaseToolWithFileAccess, register_tool
from qwen_agent.utils.utils import extract_images_from_messages


@register_tool('image_zoom_in_tool')
class ImageZoomInToolQwen3VL(BaseToolWithFileAccess):

    description = 'Zoom in on a specific region of an image by cropping it based on a bounding box (bbox) and an optional object label'
    parameters = {
        'type': 'object',
        'properties': {
            'bbox_2d': {
                'type':
                    'array',
                'items': {
                    'type': 'number'
                },
                'minItems':
                    4,
                'maxItems':
                    4,
                'description':
                    'The bounding box of the region to zoom in, as [x1, y1, x2, y2], where (x1, y1) is the top-left corner and (x2, y2) is the bottom-right corner'
            },
            'label': {
                'type': 'string',
                'description': 'The name or label of the object in the specified bounding box'
            },
            'img_idx': {
                'type': 'number',
                'description': 'The index of the zoomed-in image (starting from 0)'
            }
        },
        'required': ['bbox_2d', 'label', 'img_idx']
    }

    # Image resizing functions (copied from qwen-vl-utils)
    def round_by_factor(self, number: int, factor: int) -> int:
        """Returns the closest integer to 'number' that is divisible by 'factor'."""
        return round(number / factor) * factor

    def ceil_by_factor(self, number: int, factor: int) -> int:
        """Returns the smallest integer greater than or equal to 'number' that is divisible by 'factor'."""
        return math.ceil(number / factor) * factor

    def floor_by_factor(self, number: int, factor: int) -> int:
        """Returns the largest integer less than or equal to 'number' that is divisible by 'factor'."""
        return math.floor(number / factor) * factor

    def smart_resize(self,
                     height: int,
                     width: int,
                     factor: int = 32,
                     min_pixels: int = 56 * 56,
                     max_pixels: int = 12845056) -> tuple[int, int]:
        """Smart resize image dimensions based on factor and pixel constraints"""
        h_bar = max(factor, self.round_by_factor(height, factor))
        w_bar = max(factor, self.round_by_factor(width, factor))
        if h_bar * w_bar > max_pixels:
            beta = math.sqrt((height * width) / max_pixels)
            h_bar = self.floor_by_factor(height / beta, factor)
            w_bar = self.floor_by_factor(width / beta, factor)
        elif h_bar * w_bar < min_pixels:
            beta = math.sqrt(min_pixels / (height * width))
            h_bar = self.ceil_by_factor(height * beta, factor)
            w_bar = self.ceil_by_factor(width * beta, factor)
        return h_bar, w_bar

    def maybe_resize_bbox(self, left, top, right, bottom, img_width, img_height):
        """Resize bbox to ensure it's valid"""
        left = max(0, left)
        top = max(0, top)
        right = min(img_width, right)
        bottom = min(img_height, bottom)

        height = bottom - top
        width = right - left
        if height < 32 or width < 32:
            center_x = (left + right) / 2.0
            center_y = (top + bottom) / 2.0
            ratio = 32 / min(height, width)
            new_half_height = ceil(height * ratio * 0.5)
            new_half_width = ceil(width * ratio * 0.5)
            new_left = floor(center_x - new_half_width)
            new_right = ceil(center_x + new_half_width)
            new_top = floor(center_y - new_half_height)
            new_bottom = ceil(center_y + new_half_height)

            # Ensure the resized bbox is within image bounds
            new_left = max(0, new_left)
            new_top = max(0, new_top)
            new_right = min(img_width, new_right)
            new_bottom = min(img_height, new_bottom)

            new_height = new_bottom - new_top
            new_width = new_right - new_left

            if new_height > 32 and new_width > 32:
                return [new_left, new_top, new_right, new_bottom]
        return [left, top, right, bottom]

    def call(self, params: Union[str, dict], **kwargs) -> List[ContentItem]:
        params = self._verify_json_format_args(params)

        img_idx = params['img_idx']
        bbox = params['bbox_2d']
        images = extract_images_from_messages(kwargs.get('messages', []))
        os.makedirs(self.work_dir, exist_ok=True)

        try:
            # open image, currently only support the first image
            image_arg = images[img_idx]
            if image_arg.startswith('file://'):
                image_arg = image_arg[len('file://'):]

            if image_arg.startswith('http'):
                response = requests.get(image_arg)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
            elif os.path.exists(image_arg):
                image = Image.open(image_arg)
            else:
                image = Image.open(os.path.join(self.work_dir, image_arg))
        except Exception as e:
            logger.warning(f'{e}')
            return [ContentItem(text=f'Error: Invalid input image {images}')]

        try:
            # Validate and potentially resize bbox
            img_width, img_height = image.size
            rel_x1, rel_y1, rel_x2, rel_y2 = bbox
            abs_x1, abs_y1, abs_x2, abs_y2 = rel_x1 / 1000. * img_width, rel_y1 / 1000. * img_height, rel_x2 / 1000. * img_width, rel_y2 / 1000. * img_height

            validated_bbox = self.maybe_resize_bbox(abs_x1, abs_y1, abs_x2, abs_y2, img_width, img_height)

            left, top, right, bottom = validated_bbox

            # Crop the image
            cropped_image = image.crop((left, top, right, bottom))

            # Resize according to smart_resize logic
            new_w, new_h = self.smart_resize((right - left), (bottom - top), factor=32, min_pixels=256 * 32 * 32)
            cropped_image = cropped_image.resize((new_w, new_h), resample=Image.BICUBIC)

            output_path = os.path.abspath(os.path.join(self.work_dir, f'{uuid.uuid4()}.png'))
            cropped_image.save(output_path)

            return [ContentItem(image=output_path)]
        except Exception as e:
            obs = f'Tool Execution Error {str(e)}'
            return [ContentItem(text=obs)]
