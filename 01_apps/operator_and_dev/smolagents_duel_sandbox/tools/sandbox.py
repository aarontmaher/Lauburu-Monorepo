"""
Sandboxed Python Code Execution Engine.
=======================================
Subsystem: 01_apps/operator_and_dev/smolagents_duel_sandbox/tools/sandbox.py
"""

import time
import math
import json
from typing import Dict, Any, Optional
from ..core.config import SandboxConfig
from ..core.models import AgentAction
from .registry import SmolagentsToolRegistry

class PythonCodeSandbox:
    """Safely evaluates generated Python code-as-action strings."""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self.tools = SmolagentsToolRegistry()

    def execute_action(self, action: AgentAction) -> AgentAction:
        """Executes action's Python code in a controlled namespace."""
        t0 = time.perf_counter()
        safe_globals = {
            "__builtins__": {
                "abs": abs,
                "min": min,
                "max": max,
                "len": len,
                "round": round,
                "range": range,
                "dict": dict,
                "list": list,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "print": lambda *args: None,
            },
            "math": math,
            "json": json,
            "tools": self.tools,
        }
        safe_locals: Dict[str, Any] = {}

        try:
            exec(action.python_code, safe_globals, safe_locals)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            action.execution_time_ms = round(elapsed_ms, 3)
            action.status = "SUCCESS"
            action.output = safe_locals.get("result", safe_locals)
            action.error = None
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            action.execution_time_ms = round(elapsed_ms, 3)
            action.status = "FAILED"
            action.output = None
            action.error = str(e)

        return action
