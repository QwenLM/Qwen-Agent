from .code_interpreter import code_interpreter
from .image_gen import image_gen

# TODO: Meta info in multiple language such as en and zh.
# TODO: Use ChatGPT's schema for functions?
# TODO: These meta info should be provided by the tools' classes.
# TODO: Make this immutable once it is initialized.
list_of_all_functions = [
    {
        'name_for_human': '代码解释器',
        'name_for_model': 'code_interpreter',
        'description_for_model': '代码解释器，可用于执行Python代码。' +
        ' Enclose the code within triple backticks (`) at the beginning and end of the code.',
        'parameters': [{
            'name': 'code',
            'type': 'string',
            'description': '待执行的代码'
        }]
    },
    {
        'name_for_human':
        '文生图',
        'name_for_model':
        'image_gen',
        'description_for_model':
        '文生图是一个AI绘画（图像生成）服务，输入文本描述，返回根据文本作画得到的图片的URL。' +
        ' Format the arguments as a JSON object.',
        'parameters': [{
            'name': 'prompt',
            'description': '英文关键词，描述了希望图像具有什么内容',
            'required': True,
            'schema': {
                'type': 'string'
            },
        }],
    },
]


# TODO: Say no to these if statements.
def call_plugin(plugin_name: str, plugin_args: str) -> str:
    if plugin_name == 'code_interpreter':
        return code_interpreter(plugin_args)
    elif plugin_name == 'image_gen':
        return image_gen(plugin_args)
    else:
        raise NotImplementedError
