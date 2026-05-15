import pytest
from pydantic import TypeAdapter

from qwen_agent.llm.schema import ContentItem, Message


def test_message_type_adapter_excludes_none_fields():
    message = Message(role='assistant', content='done')

    assert message.model_dump() == {'role': 'assistant', 'content': 'done'}
    assert TypeAdapter(Message).dump_python(message) == {
        'role': 'assistant',
        'content': 'done',
    }


def test_fastapi_encoder_excludes_none_fields():
    fastapi_encoders = pytest.importorskip('fastapi.encoders')

    message = Message(role='assistant', content='done')

    assert fastapi_encoders.jsonable_encoder(message) == {
        'role': 'assistant',
        'content': 'done',
    }


def test_content_item_type_and_value_still_uses_present_field():
    item = ContentItem(text='hello')

    assert item.get_type_and_value() == ('text', 'hello')
    assert TypeAdapter(ContentItem).dump_python(item) == {'text': 'hello'}
