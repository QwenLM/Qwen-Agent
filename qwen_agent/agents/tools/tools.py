tools_list = [
        {
            'name_for_human': '代码解释器',
            'name_for_model': 'code_interpreter',
            'description_for_model': '代码解释器，可用于执行Python代码。'
            + ' Format the arguments as a JSON object.',
            'parameters': [{'name': 'code', 'type': 'string', 'description': '待执行的代码'}]
        },
        {
            'name_for_human': '文生图',
            'name_for_model': 'image_gen',
            'description_for_model': '文生图是一个AI绘画（图像生成）服务，输入文本描述，返回根据文本作画得到的图片的URL。'
            + ' Format the arguments as a JSON object.',
            'parameters': [
                {
                    'name': 'prompt',
                    'description': '英文关键词，描述了希望图像具有什么内容',
                    'required': True,
                    'schema': {'type': 'string'},
                }
            ],
        },
    ]
