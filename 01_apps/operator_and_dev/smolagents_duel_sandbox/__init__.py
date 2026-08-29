"""
SmolAgents Python Duel Sandbox Suite.
=====================================
Subsystem: 01_apps/operator_and_dev/smolagents_duel_sandbox
Version: 1.0.0-CANONICAL

Code-as-action tool registry and safe sandboxed execution engine
for autonomous agentic duelists (Hermes 3 Red vs. LuCI Blue).

Subpackages:
- core: Configs, data models, execution records
- tools: Tool registry (socket probes, latency, VRAM) and python sandbox
- presentation: Arena hub, Textual TUI HUD, and execution runners
"""

from .core import (
    SandboxConfig,
    AgentAction,
    ToolResult,
    DuelExecutionRecord,
)
from .tools import (
    SmolagentsToolRegistry,
    PythonCodeSandbox,
)
from .presentation import (
    SmolAgentsArenaHub,
    SmolAgentsDuelApp,
    run_sandbox,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "SandboxConfig",
    "AgentAction",
    "ToolResult",
    "DuelExecutionRecord",
    "SmolagentsToolRegistry",
    "PythonCodeSandbox",
    "SmolAgentsArenaHub",
    "SmolAgentsDuelApp",
    "run_sandbox",
]
