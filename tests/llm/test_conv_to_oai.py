import pytest

from qwen_agent.llm.base import BaseChatModel
from qwen_agent.llm.fncall_prompts.qwen_fncall_prompt import QwenFnCallPrompt
from qwen_agent.llm.schema import ASSISTANT, FUNCTION, USER, ContentItem, FunctionCall, Message


def test_parallel_tool_calls_unique_ids_dicts():
    # Tests that parallel tool calls in dict format without function_id get unique IDs
    messages = [
        {'role': USER, 'content': 'check weather in Beijing and Shanghai'},
        {'role': ASSISTANT, 'content': '', 'function_call': {'name': 'get_weather', 'arguments': '{"city": "Beijing"}'}},
        {'role': ASSISTANT, 'content': '', 'function_call': {'name': 'get_weather', 'arguments': '{"city": "Shanghai"}'}},
        {'role': FUNCTION, 'name': 'get_weather', 'content': 'Sunny 25C'},
        {'role': FUNCTION, 'name': 'get_weather', 'content': 'Rainy 20C'},
    ]

    oai_messages = BaseChatModel._conv_qwen_agent_messages_to_oai(messages)
    assert len(oai_messages) == 4
    assistant_msg = oai_messages[1]
    assert assistant_msg['role'] == ASSISTANT
    assert len(assistant_msg['tool_calls']) == 2

    id_0 = assistant_msg['tool_calls'][0]['id']
    id_1 = assistant_msg['tool_calls'][1]['id']
    assert id_0 != id_1

    tool_msg_0 = oai_messages[2]
    assert tool_msg_0['role'] == 'tool'
    assert tool_msg_0['id'] == id_0
    assert tool_msg_0['tool_call_id'] == id_0

    tool_msg_1 = oai_messages[3]
    assert tool_msg_1['role'] == 'tool'
    assert tool_msg_1['id'] == id_1
    assert tool_msg_1['tool_call_id'] == id_1


def test_parallel_tool_calls_duplicate_function_id():
    # Tests that parallel tool calls with duplicate function_id get deduplicated
    messages = [
        Message(role=USER, content='search info'),
        Message(role=ASSISTANT, content='', function_call=FunctionCall(name='search', arguments='{"query": "q1"}'), extra={'function_id': '1'}),
        Message(role=ASSISTANT, content='', function_call=FunctionCall(name='search', arguments='{"query": "q2"}'), extra={'function_id': '1'}),
        Message(role=FUNCTION, name='search', content='result1', extra={'function_id': '1'}),
        Message(role=FUNCTION, name='search', content='result2', extra={'function_id': '1'}),
    ]

    oai_messages = BaseChatModel._conv_qwen_agent_messages_to_oai(messages)
    assistant_msg = oai_messages[1]
    assert len(assistant_msg['tool_calls']) == 2
    id_0 = assistant_msg['tool_calls'][0]['id']
    id_1 = assistant_msg['tool_calls'][1]['id']
    assert id_0 != id_1

    assert oai_messages[2]['id'] == id_0
    assert oai_messages[2]['tool_call_id'] == id_0
    assert oai_messages[3]['id'] == id_1
    assert oai_messages[3]['tool_call_id'] == id_1


def test_existing_unique_function_ids_preserved():
    messages = [
        Message(role=USER, content='search info'),
        Message(role=ASSISTANT, content='', function_call=FunctionCall(name='search', arguments='{"query": "q1"}'), extra={'function_id': 'call_abc'}),
        Message(role=ASSISTANT, content='', function_call=FunctionCall(name='search', arguments='{"query": "q2"}'), extra={'function_id': 'call_xyz'}),
        Message(role=FUNCTION, name='search', content='result1', extra={'function_id': 'call_abc'}),
        Message(role=FUNCTION, name='search', content='result2', extra={'function_id': 'call_xyz'}),
    ]

    oai_messages = BaseChatModel._conv_qwen_agent_messages_to_oai(messages)
    assistant_msg = oai_messages[1]
    assert assistant_msg['tool_calls'][0]['id'] == 'call_abc'
    assert assistant_msg['tool_calls'][1]['id'] == 'call_xyz'
    assert oai_messages[2]['id'] == 'call_abc'
    assert oai_messages[2]['tool_call_id'] == 'call_abc'
    assert oai_messages[3]['id'] == 'call_xyz'
    assert oai_messages[3]['tool_call_id'] == 'call_xyz'


def test_multiturn_tool_calls_unique_ids():
    messages = [
        {'role': USER, 'content': 'turn 1'},
        {'role': ASSISTANT, 'content': '', 'function_call': {'name': 'f1', 'arguments': '{}'}},
        {'role': FUNCTION, 'name': 'f1', 'content': 'res1'},
        {'role': ASSISTANT, 'content': 'turn 1 done'},
        {'role': USER, 'content': 'turn 2'},
        {'role': ASSISTANT, 'content': '', 'function_call': {'name': 'f2', 'arguments': '{}'}},
        {'role': FUNCTION, 'name': 'f2', 'content': 'res2'},
    ]

    oai_messages = BaseChatModel._conv_qwen_agent_messages_to_oai(messages)
    id_t1 = oai_messages[1]['tool_calls'][0]['id']
    id_t2 = oai_messages[5]['tool_calls'][0]['id']
    assert id_t1 != id_t2
    assert oai_messages[2]['id'] == id_t1
    assert oai_messages[2]['tool_call_id'] == id_t1
    assert oai_messages[6]['id'] == id_t2
    assert oai_messages[6]['tool_call_id'] == id_t2


def test_qwen_fncall_prompt_generates_unique_ids():
    prompt_handler = QwenFnCallPrompt()
    raw_output = [
        Message(
            role=ASSISTANT,
            content=[ContentItem(text='✿FUNCTION✿: get_weather\n✿ARGS✿: {"city": "Beijing"}\n✿FUNCTION✿: get_weather\n✿ARGS✿: {"city": "Shanghai"}')]
        )
    ]

    parsed = prompt_handler.postprocess_fncall_messages(raw_output, parallel_function_calls=True)
    assert len(parsed) == 2
    assert parsed[0].extra and 'function_id' in parsed[0].extra
    assert parsed[1].extra and 'function_id' in parsed[1].extra
    assert parsed[0].extra['function_id'] != parsed[1].extra['function_id']
