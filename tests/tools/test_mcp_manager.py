import sys
import threading
import types

from qwen_agent.tools import mcp_manager


def test_concurrent_construction_initializes_singleton_once(monkeypatch):
    manager_cls = mcp_manager.MCPManager
    manager_cls._instance = None
    start = threading.Barrier(3)
    load_barrier = threading.Barrier(2)
    load_calls = []
    first_loop_started = threading.Event()
    second_loop_requested = threading.Event()
    release_first_loop = threading.Event()
    loop_lock = threading.Lock()
    loops_created = []
    instances = []

    def synchronize_load_dotenv():
        load_calls.append(threading.get_ident())
        try:
            load_barrier.wait(timeout=0.5)
        except threading.BrokenBarrierError:
            pass

    def create_loop():
        with loop_lock:
            loops_created.append(object())
            is_first = len(loops_created) == 1
        if is_first:
            first_loop_started.set()
            release_first_loop.wait(timeout=3)
        else:
            second_loop_requested.set()
        return loops_created[-1]

    monkeypatch.setattr(mcp_manager, 'load_dotenv', synchronize_load_dotenv)
    monkeypatch.setattr(mcp_manager.asyncio, 'new_event_loop', create_loop)
    monkeypatch.setattr(manager_cls, 'start_loop', lambda self: None)
    monkeypatch.setattr(manager_cls, 'monkey_patch_mcp_create_platform_compatible_process', lambda self: None)
    monkeypatch.setitem(sys.modules, 'mcp', types.ModuleType('mcp'))

    def construct():
        start.wait()
        instances.append(manager_cls())

    threads = [threading.Thread(target=construct) for _ in range(2)]
    try:
        for thread in threads:
            thread.start()
        start.wait()
        assert first_loop_started.wait(timeout=1)
        second_loop_requested.wait(timeout=0.2)
        release_first_loop.set()
        for thread in threads:
            thread.join(timeout=3)

        assert all(not thread.is_alive() for thread in threads)
        assert len(instances) == 2
        assert instances[0] is instances[1]
        assert len(load_calls) == 1
        assert len(loops_created) == 1
    finally:
        release_first_loop.set()
        for thread in threads:
            thread.join(timeout=3)
        manager_cls._instance = None
