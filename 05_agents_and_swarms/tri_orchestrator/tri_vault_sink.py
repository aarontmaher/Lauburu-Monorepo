#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Re-export TriVaultSink for 05_agents_and_swarms/tri_orchestrator module layout.
"""
import sys
import importlib.util
from pathlib import Path

_MONOREPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = _MONOREPO_ROOT / "04_data_and_memory"

if str(_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(_DATA_DIR))

try:
    from tri_vault_sink import (
        TriVaultSink,
        verify_zero_mock_compliance,
        check_storage_health,
        PRIMARY_LORA_DIR,
        SECONDARY_LORA_DIR,
        PRIMARY_OBSIDIAN_DIR,
        SECONDARY_OBSIDIAN_DIR,
    )
except ImportError:
    spec = importlib.util.spec_from_file_location("tri_vault_sink", str(_DATA_DIR / "tri_vault_sink.py"))
    if spec and spec.loader:
        tri_vault_sink_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tri_vault_sink_mod)
        TriVaultSink = tri_vault_sink_mod.TriVaultSink
        verify_zero_mock_compliance = tri_vault_sink_mod.verify_zero_mock_compliance
        check_storage_health = tri_vault_sink_mod.check_storage_health
        PRIMARY_LORA_DIR = tri_vault_sink_mod.PRIMARY_LORA_DIR
        SECONDARY_LORA_DIR = tri_vault_sink_mod.SECONDARY_LORA_DIR
        PRIMARY_OBSIDIAN_DIR = tri_vault_sink_mod.PRIMARY_OBSIDIAN_DIR
        SECONDARY_OBSIDIAN_DIR = tri_vault_sink_mod.SECONDARY_OBSIDIAN_DIR
    else:
        raise

__all__ = [
    "TriVaultSink",
    "verify_zero_mock_compliance",
    "check_storage_health",
    "PRIMARY_LORA_DIR",
    "SECONDARY_LORA_DIR",
    "PRIMARY_OBSIDIAN_DIR",
    "SECONDARY_OBSIDIAN_DIR",
]
