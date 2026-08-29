"""
SmolAgents Duel Sandbox Configuration.
======================================
Subsystem: 01_apps/operator_and_dev/smolagents_duel_sandbox/core/config.py
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

@dataclass
class SandboxConfig:
    timeout_sec: float = 1.5
    memory_limit_mb: int = 128
    allowed_modules: List[str] = ("math", "json", "time", "random", "typing")
    state_file: Path = WORKSPACE_ROOT / "00_core_infrastructure/self_healing_hub/src/smolagents_arena_state.json"
    lora_log_file: Path = WORKSPACE_ROOT / "04_data_and_memory/lora_datasets/smolagents_arena_executions.jsonl"
