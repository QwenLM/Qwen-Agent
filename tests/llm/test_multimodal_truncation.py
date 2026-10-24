"""Offline regressions for text truncation in multimodal conversations."""
import copy
from types import SimpleNamespace

import pytest

from qwen_agent.agents import Assistant
from qwen_agent.llm.base import _truncate_input_messages_roughly
from qwen_agent.llm.qwenvl_oai import QwenVLChatAtOAI
from qwen_agent.llm.schema import ContentItem, FunctionCall, Message
from qwen_agent.tools.base import BaseTool
from qwen_agent.utils.tokenization_qwen import tokenizer
from qwen_agent.utils.utils import extract_text_from_message

IMAGE = ('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0l'
         'EQVR42mP8/x8AAwMCAO+jN3sAAAAASUVORK5CYII=')
LOG = 'sensor=room_01 temperature=24.5 humidity=55 battery=90 online=true\n'


def _tokens(messages):
    return sum(
        tokenizer.count_tokens(
            str(m.function_call) if m.function_call else extract_text_from_message(m, add_upload_info=True))
        for m in messages)


@pytest.mark.parametrize('media_position', [0, 1, 2])
def test_user_text_is_shortened_without_losing_media_or_mutating_input(media_position):
    content = [ContentItem(text=LOG * 100), ContentItem(text='Additional readings. ' * 100)]
    content.insert(media_position, ContentItem(image=IMAGE))
    messages = [Message('user', content, name='operator', extra={'trace': {'id': 'test'}})]
    before = copy.deepcopy(messages)
    result = _truncate_input_messages_roughly(messages, max_tokens=256)
    assert len(result) == 1 and isinstance(result[0], Message)
    assert [item.type for item in result[0].content] == [item.type for item in content]
    assert result[0].content[media_position].image == IMAGE
    assert 0 < sum(tokenizer.count_tokens(item.text or '') for item in result[0].content) <= 256
    assert result[0].name == 'operator' and result[0].extra == messages[0].extra
    assert messages == before
    result[0].extra['trace']['id'] = 'changed'
    assert messages == before


@pytest.mark.parametrize('older_turn', [False, True])
def test_tool_result_keeps_image_and_call_identity(older_turn):
    messages = [
        Message('user', 'Inspect the thermostat.'),
        Message('assistant', '', function_call=FunctionCall('device_report', '{}'), extra={'function_id': 'call_1'}),
        Message('function', [ContentItem(text=LOG * 100), ContentItem(image=IMAGE)],
                name='device_report',
                extra={'function_id': 'call_1'}),
    ]
    if older_turn:
        messages += [Message('assistant', 'Report received.'), Message('user', 'Explain the readings.')]
    before = copy.deepcopy(messages)
    result = _truncate_input_messages_roughly(messages, max_tokens=256)
    assert all(isinstance(m, Message) for m in result)
    assert result[1] == before[1]
    assert result[2].name == 'device_report' and result[2].extra['function_id'] == 'call_1'
    assert result[2].content[1].image == IMAGE
    assert 0 < len(result[2].content[0].text) < len(before[2].content[0].text)
    assert messages == before


def test_parallel_image_result_is_unchanged_once_text_truncation_frees_enough_room():
    messages = [
        Message('user', 'Inspect the sensor log and display.'),
        Message('assistant', '', function_call=FunctionCall('sensor_log', '{}')),
        Message('assistant', '', function_call=FunctionCall('display', '{}')),
        Message('function', LOG * 100, name='sensor_log'),
        Message('function', [ContentItem(image=IMAGE)], name='display', extra={'function_id': 'image_call'}),
    ]
    before = copy.deepcopy(messages)
    result = _truncate_input_messages_roughly(messages, max_tokens=256)
    assert result[-1] == before[-1]
    assert messages == before


@pytest.mark.parametrize('media', [
    ContentItem(image=IMAGE),
    ContentItem(audio='https://example.test/audio.wav'),
    ContentItem(video=['https://example.test/frame.png']),
    ContentItem(file='device-manual.txt')
])
def test_small_text_budget_preserves_non_text_content(media):
    messages = [Message('user', [ContentItem(text=LOG * 100), media])]
    result = _truncate_input_messages_roughly(messages, max_tokens=1)
    assert isinstance(result[0], Message)
    assert result[0].content[0].text == ''
    assert result[0].content[1] == media


@pytest.mark.parametrize(
    'content',
    [LOG * 100, [ContentItem(text=LOG * 100)], [ContentItem(text=''), ContentItem(text=LOG * 100)]])
def test_text_only_messages_can_still_be_truncated(content):
    messages = [Message('user', content)]
    before = copy.deepcopy(messages)
    result = _truncate_input_messages_roughly(messages, max_tokens=128)
    assert isinstance(result[0], Message)
    assert 0 < _tokens(result) <= 128
    assert messages == before


def test_under_budget_multimodal_messages_are_unchanged():
    messages = [Message('user', [ContentItem(image=IMAGE), ContentItem(text='Read the display.')])]
    before = copy.deepcopy(messages)
    assert _truncate_input_messages_roughly(messages, max_tokens=1024) == before
    assert messages == before


@pytest.mark.parametrize('budget,lines', [(8192, 20), (8192, 500), (58000, 3000)])
@pytest.mark.parametrize('with_image', [False, True])
def test_assistant_continues_after_device_tool_result(monkeypatch, budget, lines, with_image):

    class DeviceReport(BaseTool):
        name = 'device_report'
        description = 'Read sensor telemetry and an optional display snapshot.'
        parameters = []

        def call(self, params, **kwargs):
            self.calls += 1
            items = [ContentItem(text=LOG * lines)]
            if with_image:
                items.append(ContentItem(image=IMAGE))
            return items

    tool = DeviceReport()
    tool.calls = 0
    llm = QwenVLChatAtOAI({
        'model': 'offline-vision',
        'api_key': 'unused',
        'generate_cfg': {
            'max_input_tokens': budget
        }
    })
    requests = []

    def fake_create(**kwargs):
        requests.append(copy.deepcopy(kwargs))
        answer = ('<tool_call>\n{"name": "device_report", "arguments": {}}\n</tool_call>'
                  if len(requests) == 1 else 'Sensor report inspected.')
        return iter([SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=answer))])])

    monkeypatch.setattr(llm, '_chat_complete_create', fake_create)
    bot = Assistant(llm=llm, function_list=[tool], system_message='Inspect the report. Do not control devices.')
    messages = [{'role': 'user', 'content': 'Check the display against its sensor readings.'}]
    before = copy.deepcopy(messages)
    outputs = list(bot.run(messages))
    assert tool.calls == 1 and len(requests) == 2
    assert outputs[-1][-1]['content'] == 'Sensor report inspected.'
    parts = [part for m in requests[1]['messages'] for part in m['content']]
    images = [part['image_url']['url'] for part in parts if part['type'] == 'image_url']
    assert images == ([IMAGE] if with_image else [])
    if lines > 20:
        assert tokenizer.count_tokens(LOG * lines) > budget
        sent_text = '\n'.join(part['text'] for part in parts if part['type'] == 'text')
        assert len(sent_text) < len(LOG * lines)
    assert messages == before
