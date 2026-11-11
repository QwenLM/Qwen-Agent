# Copyright 2026 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0

from typing import Any, Dict, Optional, Protocol, Union


ToolArguments = Union[str, dict]


class ToolCallDenied(Exception):
    """Raised by a lifecycle hook to prevent a tool from executing."""


class ToolLifecycleHook(Protocol):
    """Optional callbacks around an agent tool invocation.

    Hooks observe the exact arguments and result at the agent boundary. The
    ``before_tool_call`` return value is carried as metadata to the later
    callbacks; it does not replace or mutate the arguments.
    """

    def before_tool_call(self,
                         *,
                         tool_name: str,
                         tool_args: ToolArguments,
                         context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run before the tool. Raise :class:`ToolCallDenied` to reject it."""
        ...

    def after_tool_call(self,
                        *,
                        tool_name: str,
                        tool_args: ToolArguments,
                        result: Any,
                        context: Dict[str, Any],
                        metadata: Dict[str, Any]) -> None:
        """Run after a successful tool call."""
        ...

    def on_tool_error(self,
                      *,
                      tool_name: str,
                      tool_args: ToolArguments,
                      error: Exception,
                      context: Dict[str, Any],
                      metadata: Dict[str, Any]) -> None:
        """Run after a failed or rejected tool call."""
        ...
