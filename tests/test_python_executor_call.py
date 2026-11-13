from qwen_agent.tools.python_executor import PythonExecutor


def _executor_with_stub_apply():
    executor = object.__new__(PythonExecutor)
    executor.apply = lambda code: [code, '']
    return executor


def test_call_accepts_dict_params():
    executor = _executor_with_stub_apply()
    assert executor.call({'code': 'print(1)'}) == ['print(1)', '']


def test_call_accepts_json_string_params():
    executor = _executor_with_stub_apply()
    assert executor.call('{"code": "print(1)"}') == ['print(1)', '']


def test_call_accepts_fenced_code_block():
    executor = _executor_with_stub_apply()
    assert executor.call('```python\nprint(1)\n```') == ['print(1)\n', '']


def test_call_returns_empty_result_for_empty_dict_code():
    executor = _executor_with_stub_apply()
    assert executor.call({'code': '   '}) == ['', '']
