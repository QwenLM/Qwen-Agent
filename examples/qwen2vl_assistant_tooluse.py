import os
import re
import uuid
from io import BytesIO
from pprint import pprint
from typing import List, Union

import requests
from PIL import Image

from qwen_agent.agents import FnCallAgent
from qwen_agent.llm.schema import ContentItem
from qwen_agent.tools.base import BaseToolWithFileAccess, register_tool

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')


@register_tool('crop_and_resize')
class CropResize(BaseToolWithFileAccess):
    description = '这是一个放大镜功能，截取局部图像并放大从而查看更多细节，如果你无法直接看清细节时可以调用'
    parameters = [
        {
            'name': 'image',
            'type': 'string',
            'description': '输入图片本地路径或URL',
            'required': True
        },
        {
            'name': 'rectangle',
            'type': 'string',
            'description': '需要截取的局部图像区域，使用左上角坐标和右下角坐标表示（原点在图像左上角、向右为x轴正方向、向下为y轴正方向），格式：(x1,y1),(x2,y2)',
            'required': True
        },
    ]

    def _extract_coordinates(self, text):
        pattern = r'\((\d+),\s*(\d+)\)'
        matches = re.findall(pattern, text)
        coordinates = [(int(x), int(y)) for x, y in matches]
        if len(coordinates) >= 2:
            x1, y1 = coordinates[0]
            x2, y2 = coordinates[1]
            return x1, y1, x2, y2

        pattern = r'\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)'
        matches = re.findall(pattern, text)
        coordinates = [(int(x1), int(y1), int(x2), int(y2)) for x1, y1, x2, y2 in matches]
        x1, y1, x2, y2 = coordinates[0]
        return coordinates[0]

    def _expand_box(self, x1, y1, x2, y2, factor=1):
        xc = (x1 + x2) / 2
        yc = (y1 + y2) / 2
        w = x2 - x1
        h = y2 - y1
        w_new = w * factor
        h_new = h * factor
        return xc - w_new / 2, yc - h_new / 2, xc + w_new / 2, yc + h_new / 2

    def call(self, params: Union[str, dict], files: List[str] = None, **kwargs) -> List[ContentItem]:
        super().call(params=params, files=files)
        params = self._verify_json_format_args(params)

        image_arg = params['image']  # local path or url
        rectangle = params['rectangle']

        # open image
        if image_arg.startswith('http'):
            response = requests.get(image_arg)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
        elif os.path.exists(image_arg):
            image = Image.open(image_arg)
        else:
            image = Image.open(os.path.join(self.work_dir, image_arg))

        coordinates = self._extract_coordinates(rectangle)
        x1, y1, x2, y2 = self._expand_box(*coordinates, factor=1.35)

        w, h = image.size
        x1, y1 = round(x1 / 1000 * w), round(y1 / 1000 * h)
        x2, y2 = round(x2 / 1000 * w), round(y2 / 1000 * h)

        # remove padding
        x1, y1, x2, y2 = max(x1, 0), max(y1, 0), min(x2, w), min(y2, h)

        cropped_image = image.crop((x1, y1, x2, y2))

        # save
        output_path = os.path.abspath(os.path.join(self.work_dir, f'{uuid.uuid4()}.png'))
        cropped_image.save(output_path)

        return [
            ContentItem(image=output_path),
            ContentItem(text=f'（ 这张放大的局部区域的图片的URL是 {output_path} ）'),
        ]


def test():
    llm_cfg_vl = {
        # Using Qwen2-VL deployed at any openai-compatible service such as vLLM:
        # 'model_type': 'qwenvl_oai',
        # 'model': 'Qwen/Qwen2-VL-72B-Instruct',
        # 'model_server': 'http://localhost:8000/v1',  # api_base
        # 'api_key': 'EMPTY',

        # Using Qwen2-VL provided by Alibaba Cloud DashScope:
        # 'model_type': 'qwenvl_dashscope',
        # 'model': 'qwen2-vl-72b-instruct',
        # 'api_key': os.getenv('DASHSCOPE_API_KEY'),

        # TODO: Use qwen2-vl instead once qwen2-vl is released.
        'model_type': 'qwenvl_dashscope',
        'model': 'qwen-vl-max',
        'api_key': os.getenv('DASHSCOPE_API_KEY'),
        'generate_cfg': dict(max_retries=10,)
    }

    agent = FnCallAgent(function_list=['crop_and_resize'], llm=llm_cfg_vl)
    messages = [{
        'role':
            'user',
        'content': [
            {
                'image': os.path.abspath(os.path.join(ROOT_RESOURCE, 'screenshot_with_plot.jpeg'))
            },
            {
                'text': '调用工具放大右边的表格'
            },
        ],
    }]
    response = agent.run_nonstream(messages=messages)
    pprint(response, indent=4)


if __name__ == '__main__':
    test()
