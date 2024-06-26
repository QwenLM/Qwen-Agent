import os
from typing import Dict, Optional, Union

import requests

from qwen_agent.tools.base import BaseTool, register_tool


@register_tool('amap_weather')
class AmapWeather(BaseTool):
    description = '获取对应城市的天气数据'
    parameters = [{
        'name': 'location',
        'type': 'string',
        'description': '城市/区具体名称，如`北京市海淀区`请描述为`海淀区`',
        'required': True
    }]

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)

        # remote call
        self.url = 'https://restapi.amap.com/v3/weather/weatherInfo?city={city}&key={key}'

        import pandas as pd
        self.city_df = pd.read_excel(
            'https://modelscope.oss-cn-beijing.aliyuncs.com/resource/agent/AMap_adcode_citycode.xlsx')

        self.token = self.cfg.get('token', os.environ.get('AMAP_TOKEN', ''))
        assert self.token != '', 'weather api token must be acquired through ' \
            'https://lbs.amap.com/api/webservice/guide/create-project/get-key and set by AMAP_TOKEN'

    def get_city_adcode(self, city_name):
        filtered_df = self.city_df[self.city_df['中文名'] == city_name]
        if len(filtered_df['adcode'].values) == 0:
            raise ValueError(f'location {city_name} not found, availables are {self.city_df["中文名"]}')
        else:
            return filtered_df['adcode'].values[0]

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)

        location = params['location']
        response = requests.get(self.url.format(city=self.get_city_adcode(location), key=self.token))
        data = response.json()
        if data['status'] == '0':
            raise RuntimeError(data)
        else:
            weather = data['lives'][0]['weather']
            temperature = data['lives'][0]['temperature']
            return f'{location}的天气是{weather}温度是{temperature}度。'
