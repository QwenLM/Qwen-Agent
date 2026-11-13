from qwen_agent.utils.utils import extract_markdown_urls


def test_extract_markdown_urls_keeps_balanced_parentheses():
    text = '[wiki](https://en.wikipedia.org/wiki/Python_(programming_language))'
    assert extract_markdown_urls(text) == [
        'https://en.wikipedia.org/wiki/Python_(programming_language)'
    ]


def test_extract_markdown_urls_nested_parentheses():
    text = '[a](https://example.com/a_(b)) and [b](https://example.com/x)'
    assert extract_markdown_urls(text) == ['https://example.com/a_(b)', 'https://example.com/x']


def test_extract_markdown_urls_images_and_plain_links():
    text = '![img](https://example.com/a.png) and [doc](https://example.com/b)'
    assert extract_markdown_urls(text) == ['https://example.com/a.png', 'https://example.com/b']


def test_extract_markdown_urls_ignores_unbalanced_links():
    assert extract_markdown_urls('[a](https://example.com/x') == []
