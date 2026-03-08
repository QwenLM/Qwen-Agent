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

"""Tests for the Finance tool."""

import json

import pytest

from qwen_agent.tools import Finance


def test_tool_registration():
    tool = Finance()
    assert tool.name == 'finance'
    assert 'symbol' in str(tool.parameters)
    assert 'action' in str(tool.parameters)


def test_function_property():
    tool = Finance()
    func = tool.function
    assert func['name'] == 'finance'
    assert 'description' in func
    assert 'parameters' in func
    assert func['parameters']['type'] == 'object'
    assert 'symbol' in func['parameters']['properties']
    assert 'action' in func['parameters']['properties']


def test_get_price():
    tool = Finance()
    result = tool.call({'symbol': 'AAPL', 'action': 'price'})
    data = json.loads(result)
    assert data['symbol'] == 'AAPL'
    assert 'current_price' in data


@pytest.mark.parametrize('params', [
    {'symbol': 'MSFT', 'action': 'price'},
    '{"symbol": "GOOGL", "action": "price"}',
])
def test_get_price_params(params):
    tool = Finance()
    result = tool.call(params)
    data = json.loads(result)
    assert 'current_price' in data


def test_get_history():
    tool = Finance()
    result = tool.call({'symbol': 'AAPL', 'action': 'history', 'period': '5d'})
    data = json.loads(result)
    assert data['symbol'] == 'AAPL'
    assert 'data' in data
    assert 'summary' in data


def test_get_info():
    tool = Finance()
    result = tool.call({'symbol': 'AAPL', 'action': 'info'})
    data = json.loads(result)
    assert data['symbol'] == 'AAPL'
    assert 'name' in data
    assert 'sector' in data


def test_get_financials():
    tool = Finance()
    result = tool.call({'symbol': 'AAPL', 'action': 'financials'})
    data = json.loads(result)
    assert data['symbol'] == 'AAPL'
    assert 'revenue' in data
    assert 'profitability' in data


def test_invalid_symbol():
    tool = Finance()
    result = tool.call({'symbol': 'INVALID_SYMBOL_12345', 'action': 'price'})
    # Should return error message, not crash
    assert isinstance(result, str)
