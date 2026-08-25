import sys
from unittest.mock import patch

import pytest


def test_import_tools_base_without_soundfile():
    # Simulate soundfile missing from environment
    with patch.dict(sys.modules, {'soundfile': None}):
        import qwen_agent.tools.base as tools_base
        from qwen_agent.tools.base import TOOL_REGISTRY, BaseTool, register_tool

        assert hasattr(tools_base, 'BaseTool')
        assert hasattr(tools_base, 'register_tool')
        assert isinstance(TOOL_REGISTRY, dict)

        @register_tool('mock_test_tool', allow_overwrite=True)
        class MockTestTool(BaseTool):
            description = 'A mock tool for testing'
            parameters = {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'query string'
                    }
                },
                'required': ['query']
            }

            def call(self, params, **kwargs):
                return 'ok'

        assert 'mock_test_tool' in TOOL_REGISTRY
        tool = MockTestTool()
        assert tool.name == 'mock_test_tool'


def test_save_audio_to_file_raises_import_error_without_soundfile():
    from qwen_agent.utils.utils import save_audio_to_file

    with patch.dict(sys.modules, {'soundfile': None}):
        with pytest.raises(ImportError, match='Please install numpy and soundfile'):
            save_audio_to_file('dummy', 'dummy.wav')
