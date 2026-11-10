import pytest

from qwen_agent.utils.utils import extract_urls


@pytest.mark.parametrize(
    'text, expected', [
        ('See https://example.com/report.pdf. Thanks',
         ['https://example.com/report.pdf']),
        ('Read https://example.com/a, then https://example.com/b!',
         ['https://example.com/a', 'https://example.com/b']),
        ('(https://example.com/a)', ['https://example.com/a']),
        ('[https://example.com/a]', ['https://example.com/a']),
        ('https://example.com/a?b=1&c=2;', ['https://example.com/a?b=1&c=2']),
        ('https://en.wikipedia.org/wiki/Python_(programming_language)',
         ['https://en.wikipedia.org/wiki/Python_(programming_language)']),
        ('no links here', []),
    ])
def test_extract_urls_trims_prose_punctuation(text, expected):
    assert extract_urls(text) == expected
