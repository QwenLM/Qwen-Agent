from qwen_agent.tools.mcp_manager import MCPManager, _wait_for_future


class _Future:
    def __init__(self, value):
        self.value = value
        self.timeout = None

    def result(self, timeout=None):
        self.timeout = timeout
        return self.value


def test_wait_for_future_propagates_timeout():
    future = _Future("ready")

    assert _wait_for_future(future, 2.5) == "ready"
    assert future.timeout == 2.5


def test_mcp_manager_default_timeout_is_bounded():
    assert MCPManager.DEFAULT_TIMEOUT == 30.0
