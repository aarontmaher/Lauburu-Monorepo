"""
Combat Arena Configuration.
===========================
Subsystem: 01_apps/user_facing_and_scaling/combat_arena/core/config.py
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

@dataclass
class ArenaConfig:
    tick_rate_fps: int = 120
    energy_capacity: float = 100.0
    red_leader_name: str = "Hermes 3 (8B) + OpenClaw"
    blue_leader_name: str = "LuCI (OpenWrt) + Sentinel"
    state_file: Path = WORKSPACE_ROOT / "00_core_infrastructure/self_healing_hub/src/smolagents_arena_state.json"
    movesense_file: Path = WORKSPACE_ROOT / "03_biometrics_and_telemetry/movesense_readiness_live.json"
    lora_output_file: Path = WORKSPACE_ROOT / "04_data_and_memory/lora_datasets/smolagents_arena_executions.jsonl"
    default_game_mode: str = "SMOLAGENTS_PYTHON_DUEL"
