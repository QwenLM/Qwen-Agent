import json
import urllib.parse

import json5


def image_gen(plugin_args):
    prompt = json5.loads(plugin_args)['prompt']
    prompt = urllib.parse.quote(prompt)
    return json.dumps({'image_url': f'https://image.pollinations.ai/prompt/{prompt}'}, ensure_ascii=False)
