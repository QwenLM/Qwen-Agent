from types import SimpleNamespace
from unittest.mock import patch

from qwen_agent.llm.oai import TextChatAtOAI
from qwen_agent.llm.schema import Message


def _build_stream_chunk(content: str, finish_reason: str | None):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ]
    )

def test_finish_reason_non_streaming():
    with patch('openai.OpenAI') as mock_openai:
        mock_client = mock_openai.return_value
        mock_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason='stop',
                    message=SimpleNamespace(content='Hello', role='assistant'),
                )
            ]
        )
        mock_client.chat.completions.create.return_value = mock_response

        llm = TextChatAtOAI({'model': 'test-model', 'api_key': 'test-key'})
        messages = [Message('user', 'hi')]
        response = llm.chat(messages=messages, stream=False)

        assert response[0].content == 'Hello'
        assert response[0].extra['finish_reason'] == 'stop'


def test_finish_reason_streaming_delta():
    with patch('openai.OpenAI') as mock_openai:
        mock_client = mock_openai.return_value

        mock_client.chat.completions.create.return_value = [
            _build_stream_chunk('Hello', None),
            _build_stream_chunk(' world', 'stop'),
        ]

        llm = TextChatAtOAI({'model': 'test-model', 'api_key': 'test-key'})
        messages = [Message('user', 'hi')]

        # delta_stream = True
        responses = list(llm._chat_stream(messages=messages, delta_stream=True, generate_cfg={}))
        
        # Last response should have finish_reason
        assert responses[-1][0].extra['finish_reason'] == 'stop'


def test_finish_reason_streaming_no_delta():
    with patch('openai.OpenAI') as mock_openai:
        mock_client = mock_openai.return_value

        mock_client.chat.completions.create.return_value = [
            _build_stream_chunk('Hello', None),
            _build_stream_chunk(' world', 'stop'),
        ]

        llm = TextChatAtOAI({'model': 'test-model', 'api_key': 'test-key'})
        messages = [Message('user', 'hi')]

        # delta_stream = False (default)
        responses = list(llm._chat_stream(messages=messages, delta_stream=False, generate_cfg={}))

        # Last response should have full content and finish_reason
        assert responses[-1][0].content == 'Hello world'
        assert responses[-1][0].extra['finish_reason'] == 'stop'
