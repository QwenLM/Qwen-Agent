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
import re
import ssl
import urllib
import urllib.parse
import uuid
from io import BytesIO
from typing import List, Union

import requests
from PIL import Image

from qwen_agent.agents import FnCallAgent
from qwen_agent.gui import WebUI
from qwen_agent.llm.schema import ContentItem
from qwen_agent.tools.base import BaseToolWithFileAccess, register_tool

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')


@register_tool('express_tracking')
class ExpressTracking(BaseToolWithFileAccess):
    API_URL = 'https://market.aliyun.com/apimarket/detail/cmapi021863#sku=yuncode15863000017'
    description = '全国快递物流查询-快递查询接口'
    parameters = [
        {
            'name': 'no',
            'type': 'string',
            'description': '快递单号 【顺丰和丰网请输入单号:收件人或寄件人手机号后四位。例如：123456789:1234】',
            'required': True
        },
        {
            'name': 'type',
            'type': 'string',
            'description': '快递公司字母简写：不知道可不填95%能自动识别，填写查询速度会更快',
            'required': False
        },
    ]

    def call(self, params: Union[str, dict], files: List[str] = None, **kwargs) -> str:
        super().call(params=params, files=files)
        params = self._verify_json_format_args(params)

        id = params['no'].strip()
        company = params.get('type', '').strip()

        host = 'https://wuliu.market.alicloudapi.com'
        path = '/kdi'
        appcode = os.environ['AppCode_ExpressTracking']  # 开通服务后 买家中心-查看AppCode
        querys = f'no={id}&type={company}'

        url = host + path + '?' + querys
        header = {'Authorization': 'APPCODE ' + appcode}
        res = requests.get(url, headers=header)
        httpStatusCode = res.status_code

        if (httpStatusCode == 200):
            # print("正常请求计费(其他均不计费)")
            import json
            try:
                out = json.loads(res.text)
            except json.decoder.JSONDecodeError:
                import json5
                out = json5.loads(res.text)
            return '```json' + json.dumps(out, ensure_ascii=False, indent=4) + '\n```'
        else:
            httpReason = res.headers['X-Ca-Error-Message']
            if (httpStatusCode == 400 and httpReason == 'Invalid Param Location'):
                return '参数错误'
            elif (httpStatusCode == 400 and httpReason == 'Invalid AppCode'):
                return 'AppCode错误'
            elif (httpStatusCode == 400 and httpReason == 'Invalid Url'):
                return '请求的 Method、Path 或者环境错误'
            elif (httpStatusCode == 403 and httpReason == 'Unauthorized'):
                return '服务未被授权（或URL和Path不正确）'
            elif (httpStatusCode == 403 and httpReason == 'Quota Exhausted'):
                return '套餐包次数用完'
            elif (httpStatusCode == 403 and httpReason == 'Api Market Subscription quota exhausted'):
                return '套餐包次数用完，请续购套餐'
            elif (httpStatusCode == 500):
                return 'API网关错误'
            else:
                return f'参数名错误 或 其他错误 \nhttpStatusCode:{httpStatusCode} \nhttpReason: {httpReason}'


@register_tool('area_to_weather')
class Area2Weather(BaseToolWithFileAccess):
    API_URL = 'https://market.aliyun.com/apimarket/detail/cmapi010812#sku=yuncode4812000017'
    description = '地名查询天气预报，调用此API查询未来7天的天气，不支持具体时刻天气查询'
    parameters = [
        {
            'name': 'area',
            'type': 'string',
            'description': '地区名称',
            'required': True
        },
        {
            'name': 'needMoreDay',
            'type': 'string',
            'description': '是否需要返回7天数据中的后4天。1为返回，0为不返回。',
            'required': False
        },
        {
            'name': 'needIndex',
            'type': 'string',
            'description': '是否需要返回指数数据，比如穿衣指数、紫外线指数等。1为返回，0为不返回。',
            'required': False
        },
        {
            'name': 'need3HourForcast',
            'type': 'string',
            'description': '是否需要每小时数据的累积数组。由于本系统是半小时刷一次实时状态，因此实时数组最大长度为48。每天0点长度初始化为0. 1为需要 0为不',
            'required': False
        },
        {
            'name': 'needAlarm',
            'type': 'string',
            'description': '是否需要天气预警。1为需要，0为不需要。',
            'required': False
        },
        {
            'name': 'needHourData',
            'type': 'string',
            'description': '是否需要每小时数据的累积数组。由于本系统是半小时刷一次实时状态，因此实时数组最大长度为48。每天0点长度初始化为0.',
            'required': False
        },
    ]

    def call(self, params: Union[str, dict], files: List[str] = None, **kwargs) -> str:
        super().call(params=params, files=files)
        params = self._verify_json_format_args(params)

        area = urllib.parse.quote(params['area'].strip())
        needMoreDay = str(params.get('needMoreDay', 0)).strip()
        needIndex = str(params.get('needIndex', 0)).strip()
        needHourData = str(params.get('needHourData', 0)).strip()
        need3HourForcast = str(params.get('need3HourForcast', 0)).strip()
        needAlarm = str(params.get('needAlarm', 0)).strip()

        host = 'https://ali-weather.showapi.com'
        path = '/spot-to-weather'
        appcode = os.environ['AppCode_Area2Weather']  # 开通服务后 买家中心-查看AppCode
        querys = f'area={area}&needMoreDay={needMoreDay}&needIndex={needIndex}&needHourData={needHourData}&need3HourForcast={need3HourForcast}&needAlarm={needAlarm}'
        url = host + path + '?' + querys

        request = urllib.request.Request(url)
        request.add_header('Authorization', 'APPCODE ' + appcode)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        response = urllib.request.urlopen(request, context=ctx)
        byte_string = response.read()
        content = byte_string.decode('utf-8')
        return content


@register_tool('weather_hour24')
class WeatherHour24(BaseToolWithFileAccess):
    API_URL = 'https://market.aliyun.com/apimarket/detail/cmapi010812#sku=yuncode4812000017'
    description = '查询24小时预报，调用此API查询24小时内具体时间的天气'
    parameters = [
        {
            'name': 'area',
            'type': 'string',
            'description': '地区名称',
            'required': True
        },
    ]

    def call(self, params: Union[str, dict], files: List[str] = None, **kwargs) -> str:
        super().call(params=params, files=files)
        params = self._verify_json_format_args(params)

        area = urllib.parse.quote(params['area'].strip())

        host = 'https://ali-weather.showapi.com'
        path = '/hour24'
        appcode = os.environ('AppCode_weather_hour24')  # 开通服务后 买家中心-查看AppCode
        querys = f'area={area}&areaCode='
        url = host + path + '?' + querys

        request = urllib.request.Request(url)
        request.add_header('Authorization', 'APPCODE ' + appcode)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        response = urllib.request.urlopen(request, context=ctx)
        byte_string = response.read()
        content = byte_string.decode('utf-8')
        return content


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


def init_agent_service():
    llm_cfg_vl = {
        # Using Qwen2-VL deployed at any openai-compatible service such as vLLM:
        # 'model_type': 'qwenvl_oai',
        # 'model': 'Qwen2-VL-7B-Instruct',
        # 'model_server': 'http://localhost:8000/v1',  # api_base
        # 'api_key': 'EMPTY',

        # Using Qwen2-VL provided by Alibaba Cloud DashScope's openai-compatible service:
        # 'model_type': 'qwenvl_oai',
        # 'model': 'qwen-vl-max-0809',
        # 'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        # 'api_key': os.getenv('DASHSCOPE_API_KEY'),

        # Using Qwen2-VL provided by Alibaba Cloud DashScope:
        'model_type': 'qwenvl_dashscope',
        'model': 'qwen-vl-max-0809',
        'api_key': os.getenv('DASHSCOPE_API_KEY'),
        'generate_cfg': {
            'max_retries': 10,
            'fncall_prompt_type': 'qwen'
        }
    }

    tools = [
        'crop_and_resize',
        'code_interpreter',
    ]  # code_interpreter is a built-in tool in Qwen-Agent

    # API tools
    if 'AppCode_WeatherHour24' in os.environ:
        tools.append('express_tracking')
    else:
        print(f'Please get AppCode from {WeatherHour24.API_URL} and execute:\nexport AppCode_WeatherHour24=xxx')
        print('express_tracking is disabled!')

    if 'AppCode_Area2Weather' in os.environ:
        tools.append('weather_hour24')
    else:
        print(f'Please get AppCode from {Area2Weather.API_URL} and execute:\nexport AppCode_Area2Weather=xxx')
        print('weather_hour24 is disabled!')

    if 'AppCode_ExpressTracking' in os.environ:
        tools.append('area_to_weather')
    else:
        print(f'Please get AppCode from {ExpressTracking.API_URL} and execute:\nexport AppCode_ExpressTracking=xxx')
        print('area_to_weather is disabled!')

    bot = FnCallAgent(
        llm=llm_cfg_vl,
        name='Qwen2-VL',
        description='function calling',
        function_list=tools,
    )

    return bot


def test():
    # Define the agent
    bot = init_agent_service()

    # Chat
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

    for response in bot.run(messages=messages):
        print('bot response:', response)


def app_gui():
    # Define the agent
    bot = init_agent_service()

    WebUI(bot).run()


if __name__ == '__main__':
    test()
    # app_gui()
