import importlib.util
from pathlib import Path


PROMPTS_PATH = Path(__file__).parents[1] / 'agent' / 'prompts.py'
SPEC = importlib.util.spec_from_file_location('travelplanning_prompts', PROMPTS_PATH)
assert SPEC is not None and SPEC.loader is not None
PROMPTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROMPTS)
get_format_convert_prompt = PROMPTS.get_format_convert_prompt


def test_zh_conversion_prompt_preserves_missing_and_repeated_input() -> None:
    prompt = get_format_convert_prompt('zh')

    assert '每份草稿和每个 Day 段落' in prompt
    assert '没有 Budget Summary' in prompt
    assert '设为 `null`' in prompt
    assert '"current_city": "from 杭州 to 北京"' in prompt
    assert '"name": "北京金霖酒店（天安门广场前门地铁站店）"' in prompt
    assert '"mode": "walking"' not in prompt
    assert '"mode": "taxi"' not in prompt


def test_en_conversion_prompt_preserves_missing_and_repeated_input() -> None:
    prompt = get_format_convert_prompt('en')

    assert 'Preserve every draft and every Day section' in prompt
    assert 'If no Budget Summary is present' in prompt
    assert 'set every numeric budget field to `null`' in prompt
    assert '"current_city": "from Hangzhou to Beijing"' in prompt
    assert '"name": "Beijing Jinlin Hotel (Tiananmen Square Qianmen Metro Station)"' in prompt
    assert '"mode": "walking"' not in prompt
    assert '"mode": "taxi"' not in prompt
