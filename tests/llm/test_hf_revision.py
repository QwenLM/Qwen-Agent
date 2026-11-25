# Copyright 2026 The Qwen team, Alibaba Group. All rights reserved.
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

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from qwen_agent.llm.base import resolve_hf_revision_kwargs
from qwen_agent.llm.openvino import OpenVINO
from qwen_agent.llm.transformers_llm import Transformers


def _install_fake_transformers(monkeypatch):
    class _DummyTokenizer:
        pass

    fake_cfg = MagicMock(architectures=['AutoModelForCausalLM'])
    fake_tok = _DummyTokenizer()
    fake_model = MagicMock()
    fake_model.to.return_value = fake_model

    mock_auto_config = MagicMock()
    mock_auto_config.from_pretrained.return_value = fake_cfg
    mock_auto_processor = MagicMock()
    mock_auto_processor.from_pretrained.return_value = fake_tok
    mock_auto_tokenizer = MagicMock()
    mock_auto_tokenizer.from_pretrained.return_value = fake_tok
    mock_model_cls = MagicMock()
    mock_model_cls.from_pretrained.return_value = fake_model

    fake_tf = ModuleType('transformers')
    fake_tf.AutoConfig = mock_auto_config
    fake_tf.AutoProcessor = mock_auto_processor
    fake_tf.AutoTokenizer = mock_auto_tokenizer
    fake_tf.AutoModelForCausalLM = mock_model_cls
    fake_tf.PreTrainedTokenizer = _DummyTokenizer
    fake_tf.PreTrainedTokenizerFast = _DummyTokenizer
    monkeypatch.setitem(sys.modules, 'transformers', fake_tf)
    return fake_tf, fake_cfg, fake_model


def test_resolve_hf_revision_kwargs_validates_type():
    with pytest.raises(ValueError, match='must be a string'):
        resolve_hf_revision_kwargs('Qwen/Qwen3-4B', {'revision': 123})


def test_transformers_forwards_pinned_revision(monkeypatch):
    fake_tf, fake_cfg, fake_model = _install_fake_transformers(monkeypatch)

    llm = Transformers({'model': 'Qwen/Qwen3-4B', 'revision': 'abc1234'})

    assert llm.hf_model is fake_model
    fake_tf.AutoConfig.from_pretrained.assert_called_once_with('Qwen/Qwen3-4B', revision='abc1234')
    fake_tf.AutoProcessor.from_pretrained.assert_called_once_with('Qwen/Qwen3-4B', revision='abc1234')
    fake_tf.AutoModelForCausalLM.from_pretrained.assert_called_once_with(
        'Qwen/Qwen3-4B',
        config=fake_cfg,
        torch_dtype='auto',
        revision='abc1234',
    )


def test_transformers_warns_for_unpinned_hub_model_and_skips_for_local_dir(monkeypatch, tmp_path):
    fake_tf, fake_cfg, _ = _install_fake_transformers(monkeypatch)

    with patch('qwen_agent.llm.base.logger.warning') as warn_mock:
        Transformers({'model': 'Qwen/Qwen3-4B'})
        assert warn_mock.call_count == 1
        assert 'revision' in warn_mock.call_args.args[0]

    fake_tf.AutoConfig.from_pretrained.assert_called_with('Qwen/Qwen3-4B')
    fake_tf.AutoProcessor.from_pretrained.assert_called_with('Qwen/Qwen3-4B')
    fake_tf.AutoModelForCausalLM.from_pretrained.assert_called_with(
        'Qwen/Qwen3-4B',
        config=fake_cfg,
        torch_dtype='auto',
    )

    with patch('qwen_agent.llm.base.logger.warning') as warn_mock:
        Transformers({'model': str(tmp_path)})
        warn_mock.assert_not_called()


def test_openvino_forwards_pinned_revision_and_warns_when_omitted(monkeypatch, tmp_path):
    fake_tf, fake_cfg, _ = _install_fake_transformers(monkeypatch)
    fake_ov_model = MagicMock()
    mock_ov_cls = MagicMock()
    mock_ov_cls.from_pretrained.return_value = fake_ov_model

    optimum_mod = ModuleType('optimum')
    intel_mod = ModuleType('optimum.intel')
    ov_mod = ModuleType('optimum.intel.openvino')
    ov_mod.OVModelForCausalLM = mock_ov_cls
    monkeypatch.setitem(sys.modules, 'optimum', optimum_mod)
    monkeypatch.setitem(sys.modules, 'optimum.intel', intel_mod)
    monkeypatch.setitem(sys.modules, 'optimum.intel.openvino', ov_mod)

    llm = OpenVINO({'ov_model_dir': 'org/qwen-ov', 'revision': 'v1.0.0'})

    assert llm.ov_model is fake_ov_model
    fake_tf.AutoConfig.from_pretrained.assert_called_once_with('org/qwen-ov', revision='v1.0.0')
    mock_ov_cls.from_pretrained.assert_called_once_with(
        'org/qwen-ov',
        device='cpu',
        ov_config={},
        config=fake_cfg,
        revision='v1.0.0',
    )
    fake_tf.AutoTokenizer.from_pretrained.assert_called_once_with('org/qwen-ov', revision='v1.0.0')

    with patch('qwen_agent.llm.base.logger.warning') as warn_mock:
        OpenVINO({'ov_model_dir': 'org/qwen-ov'})
        assert warn_mock.call_count == 1
        assert 'revision' in warn_mock.call_args.args[0]

    fake_tf.AutoConfig.from_pretrained.assert_called_with('org/qwen-ov')
    mock_ov_cls.from_pretrained.assert_called_with(
        'org/qwen-ov',
        device='cpu',
        ov_config={},
        config=fake_cfg,
    )
    fake_tf.AutoTokenizer.from_pretrained.assert_called_with('org/qwen-ov')

    with patch('qwen_agent.llm.base.logger.warning') as warn_mock:
        OpenVINO({'ov_model_dir': str(tmp_path)})
        warn_mock.assert_not_called()
