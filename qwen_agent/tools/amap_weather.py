from qwen_agent.tools.base import BaseTool, register_tool


@register_tool('amap_weather')
class AmapWeather(BaseTool):
    name = 'amap_weather'
    description = '获取对应城市的天气数据'
    parameters = [{
        'name': 'location',
        'type': 'string',
        'description': '待查询天气的城市'
    }]

    def call(self, params: str, **kwargs) -> str:
        params = self._verify_args(params)
        if isinstance(params, str):
            return 'Parameter Error'

        raise NotImplementedError
