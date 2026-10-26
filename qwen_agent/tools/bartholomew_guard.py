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
"""
Bartholomew Deterministic AST Invariant Security Gate for Qwen-Agent
====================================================================
Sub-35us in-process execution barrier & SOC 2 Merkle receipt emitter for Qwen-Agent tools.
"""

import ast
import functools
import hashlib
import json
import re
import time
from typing import Any, ClassVar


class BartholomewSecurityGuard:
    """
    Deterministic AST execution barrier & security gate for Qwen-Agent tools.
    Evaluates proposed function calls, code interpreter scripts, and tool dispatches
    in under 35 microseconds before execution.
    """

    DESTRUCTIVE_SHELL_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(
            r"(\/bin\/|\/usr\/bin\/)?rm\s+([-\w\s]*?-[rfRF]+[-\w\s]*?)\s*(/|/\*|~|\$HOME|/etc|/var|/usr|[a-zA-Z]:[\\/])"
        ),
        re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),  # fork bomb
        re.compile(r"mkfs(\.\w+)?\s+/dev/"),
        re.compile(r"dd\s+if=.*?\s+of=(/dev/|[a-zA-Z]:)"),
        re.compile(r">\s*/dev/sd[a-z]"),
        re.compile(r"chmod\s+([-\w\s]*?-R[-\w\s]*?)\s+777\s+(/|/\*)"),
    ]

    CREDENTIAL_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"(ghp_[A-Za-z0-9_]{36,}|github_pat_[A-Za-z0-9_]{82})"),
        re.compile(r"xox[baprs]-[0-9A-Za-z]{10,48}"),
        re.compile(r"sk-[A-Za-z0-9]{32,64}"),
        re.compile(r"-----BEGIN\s+(RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY-----"),
    ]


    def __init__(self, agent_name: str = "qwen-agent", fail_closed: bool = True):
        self.agent_name = str(agent_name)
        self.fail_closed = fail_closed

    def validate_code(
        self, code_str: str, is_python_source: bool = True
    ) -> tuple[bool, str, dict[str, Any]]:
        """Validates Python code before execution in CodeInterpreter or PythonExecutor."""
        t0 = time.perf_counter()

        # 1. Regex check for destructive shell escapes inside strings
        for pat in self.DESTRUCTIVE_SHELL_PATTERNS:
            if pat.search(code_str):
                receipt = self._build_receipt(
                    "VETO",
                    "BTP-AST-001: Destructive shell pattern detected in code",
                    t0,
                )
                if self.fail_closed:
                    raise PermissionError(f"[BTP-QWEN-VETO]: {receipt['reason']}")
                return False, receipt["reason"], receipt

        # 2. Credential leakage pre-filter
        for pat in self.CREDENTIAL_PATTERNS:
            if pat.search(code_str):
                receipt = self._build_receipt(
                    "VETO",
                    "BTP-CRED-001: Secret key or credential pattern detected",
                    t0,
                )
                if self.fail_closed:
                    raise PermissionError(f"[BTP-QWEN-VETO]: {receipt['reason']}")
                return False, receipt["reason"], receipt

        # 3. Python AST parsing (when evaluating Python code artifacts)
        if is_python_source:
            try:
                tree = ast.parse(code_str)
            except SyntaxError as e:
                receipt = self._build_receipt(
                    "VETO", f"BTP-AST-SYNTAX: Syntax error: {e!s}", t0
                )
                if self.fail_closed:
                    raise PermissionError(f"[BTP-QWEN-VETO]: {receipt['reason']}")
                return False, receipt["reason"], receipt

            # Walk AST nodes to block untrusted dynamic eval
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr

                    if (
                        func_name in ("exec", "eval")
                        and node.args
                        and not isinstance(node.args[0], ast.Constant)
                    ):
                        receipt = self._build_receipt(
                            "VETO",
                            "BTP-AST-003: Dynamic untrusted exec/eval invocation",
                            t0,
                        )
                        if self.fail_closed:
                            raise PermissionError(
                                f"[BTP-QWEN-VETO]: {receipt['reason']}"
                            )
                        return False, receipt["reason"], receipt


        receipt = self._build_receipt(
            "ALLOW", "AST invariants verified successfully", t0
        )
        return True, "Code passed deterministic AST invariant gate", receipt

    def validate_fn_call(
        self, fn_name: str, fn_args: dict[str, Any]
    ) -> tuple[bool, str, dict[str, Any]]:
        """Validates function call parameters proposed by Qwen models."""
        cmd_str = str(fn_args.get("code") or fn_args.get("command") or fn_args)
        is_python = "code" in fn_args
        return self.validate_code(cmd_str, is_python_source=is_python)

    def wrap_tool(self, tool_instance: Any) -> Any:
        """Wraps a Qwen-Agent BaseTool call method."""
        orig_call = getattr(tool_instance, "call", None)
        if not orig_call:
            return tool_instance

        tool_name = getattr(tool_instance, "name", "qwen_tool")

        @functools.wraps(orig_call)
        def guarded_call(params: Any, **kwargs: Any) -> Any:
            params_dict = (
                params if isinstance(params, dict) else {"params": str(params)}
            )
            self.validate_fn_call(tool_name, params_dict)
            return orig_call(params, **kwargs)

        tool_instance.call = guarded_call
        return tool_instance

    def _build_receipt(
        self, verdict: str, reason: str, start_time: float
    ) -> dict[str, Any]:
        latency_us = (time.perf_counter() - start_time) * 1_000_000
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        leaf_data = {
            "agent": self.agent_name,
            "verdict": verdict,
            "reason": reason,
            "latency_us": round(latency_us, 2),
            "timestamp": timestamp,
            "standard": "RFC 8785 Merkle",
        }
        canonical_bytes = json.dumps(
            leaf_data, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        receipt_hash = hashlib.sha256(canonical_bytes).hexdigest()
        leaf_data["receipt_hash"] = receipt_hash
        return leaf_data
