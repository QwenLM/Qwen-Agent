import sys
from types import ModuleType


openai_stub = ModuleType('openai')
openai_stub.__version__ = '1.0.0'
openai_stub.OpenAIError = Exception
openai_stub.OpenAI = object
sys.modules.setdefault('openai', openai_stub)

from qwen_agent.llm.oai import TextChatAtOAI


def test_normalize_generate_cfg_for_oai_truncates_stop_list():
    original = {
        'temperature': 0.1,
        'stop': ['✿RESULT✿', '✿RETURN✿', 'Observation:', 'Observation:\n', '"] , "instruction":'],
    }

    normalized = TextChatAtOAI._normalize_generate_cfg_for_oai(original)

    assert normalized['stop'] == ['✿RESULT✿', '✿RETURN✿', 'Observation:', 'Observation:\n']
    assert normalized['temperature'] == 0.1
    # Keep input unchanged.
    assert len(original['stop']) == 5


def test_normalize_generate_cfg_for_oai_keeps_non_list_stop():
    original = {'stop': 'Observation:'}

    normalized = TextChatAtOAI._normalize_generate_cfg_for_oai(original)

    assert normalized == original
