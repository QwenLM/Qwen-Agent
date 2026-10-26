# Copyright 2025 The Qwen team, Alibaba Group & Bartholomew Trust Protocol. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
from pathlib import Path

# Add qwen_agent/tools to sys.path for standalone testing
tools_dir = Path(__file__).resolve().parent.parent.parent / "qwen_agent" / "tools"
sys.path.insert(0, str(tools_dir))

try:
    import bartholomew_guard

    BartholomewSecurityGuard = bartholomew_guard.BartholomewSecurityGuard
except ImportError:
    from qwen_agent.tools.bartholomew_guard import BartholomewSecurityGuard


class TestBartholomewSecurityGuard(unittest.TestCase):
    def setUp(self):
        self.guard = BartholomewSecurityGuard(
            agent_name="qwen-agent-tester", fail_closed=True
        )

    def test_safe_python_code(self):
        code = "import math\nres = [math.sqrt(x) for x in range(10)]\n"
        is_safe, _reason, receipt = self.guard.validate_code(code)

        self.assertTrue(is_safe)
        self.assertEqual(receipt["verdict"], "ALLOW")
        self.assertTrue("receipt_hash" in receipt)
        self.assertLess(receipt["latency_us"], 5000)

    def test_destructive_shell_veto(self):
        code = "import os\nos.system('rm -rf /')"
        with self.assertRaises(PermissionError) as ctx:
            self.guard.validate_code(code)
        self.assertIn("BTP-QWEN-VETO", str(ctx.exception))
        self.assertIn("BTP-AST-001", str(ctx.exception))

    def test_credential_leak_veto(self):
        code = "token = 'ghp_123456789012345678901234567890123456'"
        with self.assertRaises(PermissionError) as ctx:
            self.guard.validate_code(code)
        self.assertIn("BTP-CRED-001", str(ctx.exception))

    def test_validate_fn_call(self):
        # Safe call
        is_safe, _, _ = self.guard.validate_fn_call(
            "code_interpreter", {"code": "print(42)"}
        )
        self.assertTrue(is_safe)

        # Destructive call
        with self.assertRaises(PermissionError):
            self.guard.validate_fn_call("code_interpreter", {"code": "rm -rf /etc"})

    def test_wrap_tool(self):
        class MockQwenTool:
            name = "mock_executor"

            def call(self, params: dict):
                return "executed"

        tool = self.guard.wrap_tool(MockQwenTool())
        self.assertEqual(tool.call({"command": "git status"}), "executed")

        with self.assertRaises(PermissionError):
            tool.call({"command": "rm -rf /var"})


if __name__ == "__main__":
    unittest.main()
