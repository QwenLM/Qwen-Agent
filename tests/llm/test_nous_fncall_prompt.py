from qwen_agent.llm.fncall_prompts.nous_fncall_prompt import NousFnCallPrompt, extract_fn
from qwen_agent.llm.schema import ASSISTANT, ContentItem, Message


def test_extract_fn_keeps_empty_arguments_object():
    name, arguments = extract_fn('{"name": "search", "arguments": {}}\n')

    assert name == 'search'
    assert arguments == '{}'


def test_extract_fn_stops_after_nested_arguments_object():
    name, arguments = extract_fn('{"name": "search", "arguments": {"query": {"q": "qwen"}}}\n')

    assert name == 'search'
    assert arguments == '{"query": {"q": "qwen"}}'


def test_postprocess_incomplete_tool_call_keeps_empty_arguments():
    messages = [
        Message(
            role=ASSISTANT,
            content=[
                ContentItem(text='<tool_call>\n{"name": "search", "arguments": {}}\n'),
            ],
        ),
    ]

    parsed = NousFnCallPrompt().postprocess_fncall_messages(messages)

    assert parsed[-1].function_call.name == 'search'
    assert parsed[-1].function_call.arguments == '{}'
