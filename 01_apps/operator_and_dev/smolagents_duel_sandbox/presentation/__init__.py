"""
SmolAgents Duel Sandbox Presentation Package.
"""

from .sandbox import SmolAgentsArenaHub, SmolAgentsDuelApp, run_sandbox
from .tui import run_sandbox as run_sandbox_tui

__all__ = [
    "SmolAgentsArenaHub",
    "SmolAgentsDuelApp",
    "run_sandbox",
    "run_sandbox_tui",
]
