import logging
import os
import time
from http import HTTPStatus

import dashscope


class QwenDashscopeVLModel(object):

    def __init__(self, model, api_key):
        self.model = model
        dashscope.api_key = api_key.strip() or os.getenv('DASHSCOPE_API_KEY', default='')
        assert dashscope.api_key, 'DASHSCOPE_API_KEY is required.'

    def generate(self, prompt, stop_words=[]):
        if isinstance(prompt, str):
            prompt = [{'text': prompt}]

        MAX_TRY = 3
        count = 0
        while count < MAX_TRY:
            response = dashscope.MultiModalConversation.call(
                self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                top_p=0.01,
                top_k=1,
            )
            if response.status_code == HTTPStatus.OK:
                output = response.output.choices[0].message.content[0]['text']
                for stop_str in stop_words:
                    idx = output.find(stop_str)
                    if idx != -1:
                        output = output[:idx + len(stop_str)]
                return output
            else:
                err = 'Error code: %s, error message: %s' % (
                    response.code,
                    response.message,
                )
                logging.error(err)
                count += 1
            time.sleep(1)
