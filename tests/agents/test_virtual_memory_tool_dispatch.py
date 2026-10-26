"""Offline coverage for dispatching complete batches of virtual-memory tool calls."""
import copy
import json
from types import SimpleNamespace

import pytest

from qwen_agent.agents import VirtualMemoryAgent
from qwen_agent.llm.qwenvl_oai import QwenVLChatAtOAI
from qwen_agent.tools.base import BaseTool


class ReadDevice(BaseTool):
    name = 'read_device'
    description = 'Read a room sensor without changing its state.'
    parameters = [{'name': 'device', 'type': 'string', 'required': True}]

    def __init__(self, fail_device=None):
        super().__init__()
        self.calls = []
        self.fail_device = fail_device

    def call(self, params, **kwargs):
        device = self._verify_json_format_args(params)['device']
        self.calls.append(device)
        if device == self.fail_device:
            raise ValueError('Sensor is offline')
        return f'{device}: 24 C'


def _call(name, args):
    return '<tool_call>\n' + json.dumps({'name': name, 'arguments': args}) + '\n</tool_call>'


def _bot(monkeypatch, replies, tool, split_stream=False):
    llm = QwenVLChatAtOAI({'model': 'offline-vision', 'api_key': 'unused'})
    requests = []
    replies = iter(replies)

    def fake_create(**kwargs):
        requests.append(copy.deepcopy(kwargs))
        text = next(replies)
        if text is None:
            return iter([])
        pieces = [text[:len(text) // 2], text[len(text) // 2:]] if split_stream else [text]
        return iter(SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=p))]) for p in pieces)

    monkeypatch.setattr(llm, '_chat_complete_create', fake_create)
    return VirtualMemoryAgent(llm=llm, function_list=[tool]), requests


def _request_text(request, role=None):
    return '\n'.join(part['text'] for msg in request['messages'] if role is None or msg['role'] == role
                     for part in msg['content'] if part['type'] == 'text')


def _assert_results_match_calls(response):
    calls = [m for m in response if m.get('function_call')]
    results = [m for m in response if m['role'] == 'function']
    assert len(results) == len(calls)
    for call, result in zip(calls, results):
        assert result['name'] == call['function_call']['name']
        assert result['extra']['function_id'] == call['extra']['function_id']
    return results


@pytest.mark.parametrize('split_stream', [False, True])
@pytest.mark.parametrize('devices', [['bedroom'], ['bedroom', 'living_room'], ['bedroom', 'living_room', 'kitchen']])
def test_executes_each_call_once_and_returns_all_results(monkeypatch, split_stream, devices):
    reply = 'Checking the sensors.\n' + '\n'.join(_call('read_device', {'device': d}) for d in devices)
    tool = ReadDevice()
    bot, requests = _bot(monkeypatch, [reply, 'Readings compared.'], tool, split_stream)
    messages = [{'role': 'user', 'content': 'Compare the room temperatures.'}]
    before = copy.deepcopy(messages)
    responses = list(bot.run(messages))
    assert tool.calls == devices
    results = _assert_results_match_calls(responses[-1])
    assert [r['content'] for r in results] == [f'{d}: 24 C' for d in devices]
    assert len(requests) == 2
    assert all(f'{d}: 24 C' in _request_text(requests[1]) for d in devices)
    assert responses[-1][-1]['content'] == 'Readings compared.'
    assert messages == before


def test_failed_tool_does_not_skip_other_calls(monkeypatch):
    reply = '\n'.join(_call('read_device', {'device': d}) for d in ['bedroom', 'living_room'])
    tool = ReadDevice(fail_device='bedroom')
    bot, requests = _bot(monkeypatch, [reply, 'One sensor is offline.'], tool)
    response = bot.run_nonstream([{'role': 'user', 'content': 'Read both sensors.'}])
    assert tool.calls == ['bedroom', 'living_room']
    results = _assert_results_match_calls(response)
    assert 'Sensor is offline' in results[0]['content']
    assert results[1]['content'] == 'living_room: 24 C'
    assert len(requests) == 2


@pytest.mark.parametrize('retrieval_first', [False, True])
def test_retrieval_and_device_call_both_execute(monkeypatch, tmp_path, retrieval_first):
    manual = tmp_path / 'thermostat.txt'
    manual.write_text('THERMOSTAT_MANUAL: recommended operating range is 16 to 28 C.', encoding='utf-8')
    calls = [
        _call('retrieval', {
            'query': 'operating range',
            'files': [str(manual)]
        }),
        _call('read_device', {'device': 'bedroom'})
    ]
    if not retrieval_first:
        calls.reverse()
    tool = ReadDevice()
    bot, requests = _bot(monkeypatch, ['\n'.join(calls), 'The reading is in range.'], tool)
    response = bot.run_nonstream([{'role': 'user', 'content': 'Check the sensor against its manual.'}])
    assert tool.calls == ['bedroom']
    results = _assert_results_match_calls(response)
    assert {r['name'] for r in results} == {'retrieval', 'read_device'}
    assert len(requests) == 2
    assert 'THERMOSTAT_MANUAL' in _request_text(requests[1], role='system')
    assert 'bedroom: 24 C' in _request_text(requests[1])


def test_keeps_knowledge_from_each_retrieval_in_one_batch(monkeypatch, tmp_path):
    calls = []
    for marker in ['BEDROOM_MANUAL', 'LIVING_ROOM_MANUAL']:
        manual = tmp_path / f'{marker}.txt'
        manual.write_text(f'{marker}: recommended temperature is 24 C.', encoding='utf-8')
        calls.append(_call('retrieval', {'query': 'temperature', 'files': [str(manual)]}))
    bot, requests = _bot(monkeypatch, ['\n'.join(calls), 'Both manuals checked.'], ReadDevice())
    response = bot.run_nonstream([{'role': 'user', 'content': 'Compare both manuals.'}])
    _assert_results_match_calls(response)
    assert len(requests) == 2
    system = _request_text(requests[1], role='system')
    assert 'BEDROOM_MANUAL' in system and 'LIVING_ROOM_MANUAL' in system


def test_plain_reply_has_no_duplicate_terminal_yield(monkeypatch):
    tool = ReadDevice()
    bot, requests = _bot(monkeypatch, ['Hello.'], tool)
    responses = list(bot.run([{'role': 'user', 'content': 'Hello.'}]))
    assert len(responses) == 1
    assert responses[0][-1]['content'] == 'Hello.'
    assert tool.calls == [] and len(requests) == 1


def test_later_model_step_does_not_replay_previous_calls(monkeypatch):
    first = '\n'.join(_call('read_device', {'device': d}) for d in ['bedroom', 'living_room'])
    second = _call('read_device', {'device': 'kitchen'})
    tool = ReadDevice()
    bot, requests = _bot(monkeypatch, [first, second, 'All rooms checked.'], tool)
    response = bot.run_nonstream([{'role': 'user', 'content': 'Check all rooms.'}])
    assert tool.calls == ['bedroom', 'living_room', 'kitchen']
    _assert_results_match_calls(response)
    assert len(requests) == 3
    assert all(f'{device}: 24 C' in _request_text(requests[-1]) for device in tool.calls)


def test_later_retrieval_step_refreshes_previous_knowledge(monkeypatch, tmp_path):
    replies = []
    for marker in ['OLD_MANUAL', 'CURRENT_MANUAL']:
        manual = tmp_path / f'{marker}.txt'
        manual.write_text(f'{marker}: temperature specification.', encoding='utf-8')
        replies.append(_call('retrieval', {'query': 'temperature', 'files': [str(manual)]}))
    bot, requests = _bot(monkeypatch, replies + ['Current manual checked.'], ReadDevice())
    response = bot.run_nonstream([{'role': 'user', 'content': 'Find the current manual.'}])
    _assert_results_match_calls(response)
    assert len(requests) == 3
    assert 'OLD_MANUAL' in _request_text(requests[1], role='system')
    system = _request_text(requests[2], role='system')
    assert 'CURRENT_MANUAL' in system and 'OLD_MANUAL' not in system


def test_empty_initial_reply_has_a_result_for_run_nonstream(monkeypatch):
    tool = ReadDevice()
    bot, requests = _bot(monkeypatch, [None, None], tool)
    assert list(bot.run([{'role': 'user', 'content': 'Hello.'}])) == [[]]
    assert bot.run_nonstream([{'role': 'user', 'content': 'Hello.'}]) == []
    assert tool.calls == [] and len(requests) == 2


def test_empty_reply_after_tools_does_not_repeat_execution(monkeypatch):
    tool = ReadDevice()
    bot, requests = _bot(monkeypatch, [_call('read_device', {'device': 'bedroom'}), None], tool)
    responses = list(bot.run([{'role': 'user', 'content': 'Read the sensor.'}]))
    assert tool.calls == ['bedroom'] and len(requests) == 2
    assert responses[-1][-1]['role'] == 'function'
    assert len(responses) == 2
