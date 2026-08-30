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

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from threading import Event

REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_package(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module


def _load_module(name: str, relative_path: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_ensure_package('qwen_agent', REPO_ROOT / 'qwen_agent')
_ensure_package('qwen_agent.llm', REPO_ROOT / 'qwen_agent' / 'llm')
_ensure_package('qwen_agent.utils', REPO_ROOT / 'qwen_agent' / 'utils')
_load_module('qwen_agent.log', 'qwen_agent/log.py')
_load_module('qwen_agent.settings', 'qwen_agent/settings.py')
schema_module = _load_module('qwen_agent.llm.schema', 'qwen_agent/llm/schema.py')
_load_module('qwen_agent.utils.tokenization_qwen', 'qwen_agent/utils/tokenization_qwen.py')
_load_module('qwen_agent.utils.utils', 'qwen_agent/utils/utils.py')
_load_module('qwen_agent.llm.base', 'qwen_agent/llm/base.py')
_load_module('qwen_agent.llm.function_calling', 'qwen_agent/llm/function_calling.py')
transformers_llm_module = _load_module('qwen_agent.llm.transformers_llm', 'qwen_agent/llm/transformers_llm.py')

Message = schema_module.Message
Transformers = transformers_llm_module.Transformers


class _FakeTensor:

    def __init__(self, values=None):
        self.values = values or [[]]

    def size(self, dim):
        assert dim == -1
        return 1

    def tolist(self):
        return self.values


class _FakeResponse:

    def __getitem__(self, key):
        return self


class _FakeTokenizer:

    def __init__(self):
        self.decoded_inputs = []

    def decode(self, tokens):
        self.decoded_inputs.append(tokens)
        return ''.join(tokens)

    def batch_decode(self, response, skip_special_tokens=True):
        return ['done']


class _FakeModel:

    def __init__(self):
        self.calls = []
        self.completed = Event()

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        self.completed.set()
        return _FakeResponse()


class _FakeStreamer:

    def __init__(self, completed):
        self.completed = completed

    def __iter__(self):
        assert self.completed.wait(timeout=1)
        return iter(['done'])


class _FakeStoppingCriteria:
    pass


class _FakeStoppingCriteriaList(list):
    pass


def _install_fake_transformers_modules():
    set_seed_calls = []

    fake_transformers = types.ModuleType('transformers')

    def set_seed(seed):
        set_seed_calls.append(seed)

    fake_transformers.set_seed = set_seed
    fake_generation = types.ModuleType('transformers.generation')
    fake_stopping_criteria = types.ModuleType('transformers.generation.stopping_criteria')
    fake_stopping_criteria.StoppingCriteria = _FakeStoppingCriteria
    fake_stopping_criteria.StoppingCriteriaList = _FakeStoppingCriteriaList

    return set_seed_calls, {
        'transformers': fake_transformers,
        'transformers.generation': fake_generation,
        'transformers.generation.stopping_criteria': fake_stopping_criteria,
    }


class TransformersStopHandlingTest(unittest.TestCase):

    def setUp(self):
        self.llm = Transformers.__new__(Transformers)
        self.llm.hf_model = _FakeModel()
        self.llm.tokenizer = _FakeTokenizer()
        self.llm._get_inputs = lambda messages: {'input_ids': _FakeTensor()}
        self.llm._get_streamer = lambda: _FakeStreamer(self.llm.hf_model.completed)
        self.messages = [Message(role='user', content='hi')]
        self.generate_cfg = {'stop': ['Observation:'], 'seed': 123, 'temperature': 0.1}
        self.set_seed_calls, self.fake_modules = _install_fake_transformers_modules()
        self.original_modules = {name: sys.modules.get(name) for name in self.fake_modules}
        sys.modules.update(self.fake_modules)

    def tearDown(self):
        for name, module in self.original_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def test_chat_no_stream_translates_stop_to_stopping_criteria(self):
        response = self.llm._chat_no_stream(self.messages, self.generate_cfg)

        self.assertEqual(response[-1].content, 'done')
        self.assertEqual(self.set_seed_calls, [123])
        kwargs = self.llm.hf_model.calls[-1]
        self.assertNotIn('stop', kwargs)
        self.assertNotIn('seed', kwargs)
        self.assertIn('stopping_criteria', kwargs)
        self.assertIsInstance(kwargs['stopping_criteria'], _FakeStoppingCriteriaList)
        self.assertEqual(len(kwargs['stopping_criteria']), 1)
        criteria = kwargs['stopping_criteria'][0]
        self.assertTrue(criteria(_FakeTensor([['prefix ', 'Observation:']]), scores=None))
        self.assertFalse(criteria(_FakeTensor([['prefix']]), scores=None))

    def test_chat_stream_translates_stop_to_stopping_criteria(self):
        chunks = list(self.llm._chat_stream(self.messages, delta_stream=False, generate_cfg=self.generate_cfg))

        self.assertEqual(chunks[-1][-1].content, 'done')
        self.assertEqual(self.set_seed_calls, [123])
        kwargs = self.llm.hf_model.calls[-1]
        self.assertNotIn('stop', kwargs)
        self.assertNotIn('seed', kwargs)
        self.assertIn('streamer', kwargs)
        self.assertIn('stopping_criteria', kwargs)
        self.assertIsInstance(kwargs['stopping_criteria'], _FakeStoppingCriteriaList)
        self.assertEqual(len(kwargs['stopping_criteria']), 1)


if __name__ == '__main__':
    unittest.main()
