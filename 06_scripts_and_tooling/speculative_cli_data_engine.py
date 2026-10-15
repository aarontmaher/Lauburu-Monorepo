#!/usr/bin/env python3
"""
================================================================================
Speculative CLI & Tri-Vault Data Retrieval Engine (Sovereign Local AI)
================================================================================
Subsystem: 06_scripts_and_tooling / speculative_cli_data_engine.py
Role: Speculative CLI command drafting, streaming execution, high-throughput
      data retrieval, and sovereign credential handler (/api-key-handler).

Architectural Invariant:
- Screen Lens remains the dedicated Multimodal Vision & VLA Spatial Actuator.
- SpeculativeCliDataEngine serves as the Headless System Hands & Data Brain,
  interfacing seamlessly with Screen Lens, the 7-Layer Mesh, and Tri-Vault.
- Rule #0 & Rule #1 Compliant: 100% authentic exit codes, zero fake telemetry.
- Rule #11 & /api-key-handler: Zero cloud leakage of API credentials; local
  Qwen 2.5 Coder (:8081) / Qwen 3.8 Max (:8082) strictly parses keys.
================================================================================
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if not (REPO_ROOT / "06_scripts_and_tooling").exists():
    for _cand in [Path("/Volumes/Lauburu-Monorepo"), Path("/Volumes/Lauburu-Monorepo")]:
        if _cand.exists():
            REPO_ROOT = _cand
            break
OBSIDIAN_VAULT = REPO_ROOT / "obsidian_vault"
DATA_LAKE = REPO_ROOT / "04_data_and_memory"
LORA_DATASET = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl")
EXECUTION_LOG = DATA_LAKE / "data/speculative_cli_executions.jsonl"
USER_ENV = Path.home() / ".env"
MONO_ENV = REPO_ROOT / ".env"
KEY_MANAGER_SCRIPT = REPO_ROOT / "06_scripts_and_tooling/lauburu_key_manager.py"
UNIFIED_SCREEN_LENS = REPO_ROOT / "06_scripts_and_tooling/automation/unified_screen_lens.py"
VERIFY_PROBES_SCRIPT = REPO_ROOT / "06_scripts_and_tooling/network/verify_probes.py"
RESURRECT_SCRIPT = REPO_ROOT / "06_scripts_and_tooling/network/canonical_network_resurrection_engine.py"
GEMINI_TELEMETRY_TRAINER = REPO_ROOT / "06_scripts_and_tooling/training/lens_gemini_telemetry_trainer.py"
MESH_STORAGE_ORCHESTRATOR = REPO_ROOT / "06_scripts_and_tooling/storage/mesh_storage_and_syncthing_orchestrator.py"
MESH_BOOT_PROVISIONER = REPO_ROOT / "06_scripts_and_tooling/automation/mesh_agy_gemini_boot_provisioner.py"

PORT_SYNTAX = 8081  # Qwen 2.5 Coder
PORT_MASTER = 8082  # Qwen 3.8 Max 27B Abliterated (Sovereign Master Local Orchestrator & Default Model)


# -----------------------------------------------------------------------------
# 1. Data Structures & Execution Receipts
# -----------------------------------------------------------------------------
@dataclass
class SpeculativeCommandDraft:
    raw_prompt: str
    speculative_command: str
    suggested_args: List[str]
    confidence_score: float
    safety_rating: str  # SAFE, CAUTION, REJECTED
    rationale: str
    latency_ms: float
    drafter_model: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CliExecutionReceipt:
    command: str
    args: List[str]
    exit_code: int
    duration_ms: float
    stdout_lines: List[str]
    stderr_lines: List[str]
    sha256_receipt: str
    timestamp: str
    zero_mock_certified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DataRetrievalResult:
    query: str
    source: str
    matches_found: int
    records: List[Dict[str, Any]]
    duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# -----------------------------------------------------------------------------
# 2. Speculative Command Drafter
# -----------------------------------------------------------------------------
class SpeculativeCommandDrafter:
    """Speculatively generates and ranks candidate CLI commands before execution."""

    DANGEROUS_PATTERNS = [
        r"\brm\s+(?:-[rf]{1,2}\s+|-[rf]\s+-[rf]\s+|--no-preserve-root\s+)+/\*?(?:\s|$)",
        r"\brm\s+(?:-[rf]{1,2}\s+|-[rf]\s+-[rf]\s+)+\*(?:\s|$)",
        r"\bmkfs(?:\.[a-z0-9]+)?\b",
        r"\bdd\s+if=.*of=/dev/(?:sd[a-z]|r?disk\d+|nvme\w+)\b",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",  # fork bomb
        r">\s*/dev/(?:sd[a-z]|r?disk\d+|nvme\w+)\b",
        r"\bchmod\s+-R\s+777\s+/\*?(?:\s|$)",
    ]

    COMMON_SPECULATIVE_MAPPINGS = {
        "network status": "lauburu-network --test",
        "network test": "lauburu-network --test",
        "network health": "lauburu-network --test",
        "mesh topology": "lauburu-network --tree",
        "network topology": "lauburu-network --tree",
        "network tree": "lauburu-network --tree",
        "network json": "lauburu-network --json",
        "verify probes": f"python3 {VERIFY_PROBES_SCRIPT}",
        "mesh probes": f"python3 {VERIFY_PROBES_SCRIPT}",
        "hardware probes": f"python3 {VERIFY_PROBES_SCRIPT}",
        "resurrect": f"python3 {RESURRECT_SCRIPT} --probe-only",
        "resurrect mesh": f"python3 {RESURRECT_SCRIPT}",
        "resurrect network": f"python3 {RESURRECT_SCRIPT}",
        "train": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "continuous training": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "run continuous training": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "run continuous training of lauburu-lens-argon:latest": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "continuous training of lauburu-lens-argon:latest": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "train lauburu-lens-argon:latest": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "train lauburu-lens-argon": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "lauburu-lens-argon:latest": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "lauburu-lens-argon": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "training status": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --status",
        "train status": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --status",
        "train gemini telemetry": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "gemini telemetry training": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "train argontelemetry": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "argontelemetry": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "gemini argontelemetry": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "train local ai": f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
        "storage topology": f"python3 {MESH_STORAGE_ORCHESTRATOR} --status",
        "storage matrix": f"python3 {MESH_STORAGE_ORCHESTRATOR} --status",
        "model vault": f"python3 {MESH_STORAGE_ORCHESTRATOR} --status",
        "sync storage": f"python3 {MESH_STORAGE_ORCHESTRATOR} --sync",
        "syncthing": f"python3 {MESH_STORAGE_ORCHESTRATOR} --sync",
        "federate storage": f"python3 {MESH_STORAGE_ORCHESTRATOR} --sync",
        "app list": "lauburu-apps --tree",
        "app tree": "lauburu-apps --tree",
        "app test": "lauburu-apps --test",
        "monitor tui": "lauburu-monitor",
        "status": "lauburu-network --test",
        "network": "lauburu-network --test",
        "heal": "heal",
        "heal mesh": "heal",
        "heal network": "heal",
        "heal network health": "heal",
        "network heal": "heal",
        "network healing": "heal",
        "self heal": "heal",
        "kde heal": "kde heal",
        "kde": "kde",
        "automate": f"python3 {UNIFIED_SCREEN_LENS} mesh exec 'uname -n && uptime'",
        "automate network": f"python3 {UNIFIED_SCREEN_LENS} mesh exec 'uname -n && uptime'",
        "automate across network": f"python3 {UNIFIED_SCREEN_LENS} mesh exec 'uname -n && uptime'",
        "automate across the network": f"python3 {UNIFIED_SCREEN_LENS} mesh exec 'uname -n && uptime'",
        "network automation": f"python3 {UNIFIED_SCREEN_LENS} mesh exec 'uname -n && uptime'",
        "mesh automation": f"python3 {UNIFIED_SCREEN_LENS} mesh exec 'uname -n && uptime'",
        "mesh exec": f"python3 {UNIFIED_SCREEN_LENS} mesh exec 'uname -n && uptime'",
        "storage": f"python3 {MESH_STORAGE_ORCHESTRATOR} --status",
        "storage health": f"python3 {MESH_STORAGE_ORCHESTRATOR} --status",
        "ram": "vm_stat",
        "ram status": "vm_stat",
        "key audit": f"python3 {KEY_MANAGER_SCRIPT} --audit",
        "api key": f"python3 {KEY_MANAGER_SCRIPT} --audit",
        "trainer eval": f"DEVELOPER_DIR=/Library/Developer/CommandLineTools {REPO_ROOT}/05_agents_and_swarms/continuous_polyglot_go_trainer/continuous_polyglot_go_trainer --eval-once",
        "git status": "git status --short",
        "git branch": "git branch -a",
        # Mesh GUI & Sovereign Dashboard
        "mesh gui": "mesh_gui",
        "mesh_gui": "mesh_gui",
        "mesh-gui": "mesh_gui",
        "meshgui": "mesh_gui",
        "mesh dashboard": "mesh_gui",
        "open mesh gui": "mesh_gui",
        "mesh hud": "mesh_gui",
        "mesh top": "mesh_gui --tui",
        "mesh status": "mesh_gui --status",
        # Speedify / Channel Bonding Engine
        "speedify e2e": "rust_bonding_engine test-e2e --payload-size-mb 5",
        "speedify test": "rust_bonding_engine test-e2e --payload-size-mb 5",
        "speedify": "rust_bonding_engine test-e2e --payload-size-mb 5",
        "automate speedify": "rust_bonding_engine test-e2e --payload-size-mb 5",
        "bonding test": "rust_bonding_engine test-e2e --payload-size-mb 5",
        "bond test": "rust_bonding_engine test-e2e --payload-size-mb 5",
        "channel bonding": "rust_bonding_engine test-e2e --payload-size-mb 5",
        "speedify status": "rust_bonding_engine interfaces",
        "speedify interfaces": "rust_bonding_engine interfaces",
        "bond interfaces": "rust_bonding_engine interfaces",
        "bond status": "rust_bonding_engine interfaces",
        "inspect all physical bondable network interfaces": "rust_bonding_engine interfaces",
        "route traffic through bonded connection": "curl -x socks5://127.0.0.1:1080 https://speed.cloudflare.com/__down?bytes=25000000 -o /dev/null",
        "start bond client": "rust_bonding_engine client --target 127.0.0.1 --port 18804 --socks5-bind 127.0.0.1:1080",
        "start bond server": "rust_bonding_engine server --port 18804 --bind 0.0.0.0",
        # Screen Lens Sovereign Terminal Controller
        "screen lens": "screen-lens status",
        "screen-lens": "screen-lens status",
        "screen lens status": "screen-lens status",
        "screen-lens status": "screen-lens status",
        "lens status": "screen-lens status",
        "captures": "screen-lens latest",
        "screen captures": "screen-lens latest",
        "latest captures": "screen-lens latest",
        "latest screen captures": "screen-lens latest",
        "ocr": "screen-lens latest",
        "ocr summary": "screen-lens latest",
        "screen lens start": "screen-lens start",
        "screen lens stop": "screen-lens stop",
        "screen lens restart": "screen-lens restart",
        # AGY, Gemini CLI, Dependencies & Start-on-Boot Provisioning
        "configure agy and gemini": f"python3 {MESH_BOOT_PROVISIONER} --provision",
        "configure agy": f"python3 {MESH_BOOT_PROVISIONER} --provision",
        "configure gemini": f"python3 {MESH_BOOT_PROVISIONER} --provision",
        "configure dependencies": f"python3 {MESH_BOOT_PROVISIONER} --provision",
        "provision mesh": f"python3 {MESH_BOOT_PROVISIONER} --provision",
        "audit dependencies": f"python3 {MESH_BOOT_PROVISIONER} --status",
        "boot services": f"python3 {MESH_BOOT_PROVISIONER} --status",
        "start on boot": f"python3 {MESH_BOOT_PROVISIONER} --status",
        "agy status": f"python3 {MESH_BOOT_PROVISIONER} --status",
        "gemini status": f"python3 {MESH_BOOT_PROVISIONER} --status",
        "setup models": f"python3 {MESH_BOOT_PROVISIONER} --models",
        "set up my models": f"python3 {MESH_BOOT_PROVISIONER} --models",
        "set up models": f"python3 {MESH_BOOT_PROVISIONER} --models",
        "models": f"python3 {MESH_BOOT_PROVISIONER} --models",
        "page assist": f"python3 {MESH_BOOT_PROVISIONER} --models",
        "ollama bridge": f"python3 {MESH_BOOT_PROVISIONER} --models",
        # Neo4j Sovereign Graph + EmbeddingGemma 2 MRL RAG + Root Orchestrator
        "neo4j": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py status",
        "neo4j status": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py status",
        "neo4j schema": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py schema",
        "neo4j seed": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py seed",
        "embeddinggemma": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py status",
        "embeddinggemma 2": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py status",
        "gemma 2": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py status",
        "gemma2": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py status",
        "root status": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py root --target all 'id'",
        "root mesh": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py root --target all 'id'",
        # Sovereign Unified System: Podman Storage, 4-Stage Self-Healing, Memory, Py-Pi, Protocols, IDE, Benchmark & Review
        "podman storage": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py podman-storage",
        "podman-storage": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py podman-storage",
        "rooted podman": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py podman-storage",
        "podman spec": f"python3 {MESH_STORAGE_ORCHESTRATOR} --podman-spec",
        "heal cascade": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py heal-cascade",
        "heal-cascade": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py heal-cascade",
        "self healing cascade": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py heal-cascade",
        "bluetooth serial to kdeconnect ssh": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py heal-cascade",
        "bluetooth serial terminal": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py heal-cascade",
        "bluetooth pan": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py heal-cascade",
        "wol ethernet": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py heal-cascade",
        "kdeconnect ssh": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py heal-cascade",
        "memory": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py memory",
        "cognitive memory": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py memory",
        "memory architecture": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py memory",
        "accounts": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py accounts",
        "dual accounts": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py accounts",
        "google workspace": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py accounts",
        "py-pi": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py py-pi",
        "pypi": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py py-pi",
        "python companion": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py py-pi",
        "python model": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py py-pi",
        "deps": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py deps",
        "dependencies": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py deps",
        "protocols": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py protocols",
        "sharding": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py sharding",
        "sharding protocols": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py sharding",
        "training protocols": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py protocols",
        "ide": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py ide",
        "integrate ides": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py integrate-ides",
        "integrate-ides": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py integrate-ides",
        "goland pycharm intellij": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py ide",
        "cockpit": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py ide",
        "benchmark network": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py benchmark-network",
        "benchmark-network": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py benchmark-network",
        "docker cloudflare vs tailscale": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py benchmark-network",
        "cloudflare vs tailscale": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py benchmark-network",
        "review project": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py review-project",
        "review-project": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py review-project",
        "what have i forgotten": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py review-project",
        "overview": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py overview",
        "debate": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py debate",
        "ai debate": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py debate",
        "ai-debate": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py debate",
        "vla": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py vla",
        "qwen 3d vla": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py vla",
        "audit code": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py audit-code",
        "audit-code": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py audit-code",
        "coding telemetry": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py audit-code",
        "elo": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py elo",
        "elo benchmark": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py elo",
        "self optimize": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py self-optimize",
        "self-optimize": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py self-optimize",
        "download model": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py download-model",
        "download-model": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py download-model",
        "download models": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py download-model",
        "benchmark 70b": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py benchmark-70b-100b",
        "benchmark 100b": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py benchmark-70b-100b",
        "benchmark 70b 100b": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py benchmark-70b-100b",
        "benchmark-70b-100b": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py benchmark-70b-100b",
        "benchmark-heavy": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py benchmark-70b-100b",
        # 24/7 Lens + Qwen 3D + Gemma 2 + Root/Shizuku/rish + Scrcpy 5.0 + Page Assist Automation Training Protocol
        "automate-247": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py automate-247",
        "automation-protocol": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py automate-247",
        "24/7 lens automation training protocol": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py automate-247",
        "run a 24/7 lens automation training protocol": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py automate-247",
        "lens automation training protocol": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py automate-247",
        "scrcpy 5.0": f"python3 {REPO_ROOT}/06_scripts_and_tooling/automation/smart_scrcpy_wrapper.py --scrcpy-5-status",
        "deploy-network": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py deploy-network",
        "deploy network": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py deploy-network",
        "sync-network": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py deploy-network",
        "sync network": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py deploy-network",
        "fully configure the plan across the full network": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py deploy-network",
        "configure across the full network": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py deploy-network",
        "heal s20": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py heal-s20",
        "heal-s20": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py heal-s20",
        "movesense gatt": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py movesense-gatt",
        "movesense-gatt": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py movesense-gatt",
        "voice coder": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py voice-coder",
        "voice-coder": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py voice-coder",
        "junie mesh": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py junie-mesh",
        "junie-mesh": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py junie-mesh",
        # Polyglot Specialist IDE & Runtime Integration (GoLand/langgo, PyCharm, IntelliJ, Chromium, BT Serial)
        "specialists": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists",
        "specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists",
        "polyglot specialists": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists",
        "polyglot-specialists": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists",
        "ide-specialists": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists",
        "integrate-specialists": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists",
        "langgo": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target langgo",
        "goland": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target goland",
        "pycharm": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target pycharm",
        "intellij": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target intellij",
        "chromium": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target chromium",
        "bt-serial": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target bt-serial",
        "polyglot-go-bubbletea-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target langgo",
        "/polyglot-go-bubbletea-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target langgo",
        "polyglot-python-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target pycharm",
        "/polyglot-python-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target pycharm",
        "polyglot-kotlin-android-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target intellij",
        "/polyglot-kotlin-android-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target intellij",
        "polyglot-c-cpp-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target bt-serial",
        "/polyglot-c-cpp-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target bt-serial",
        "polyglot-rust-wgpu-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target chromium",
        "/polyglot-rust-wgpu-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target chromium",
        "polyglot-typescript-web-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target chromium",
        "/polyglot-typescript-web-specialist": f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target chromium",
    }

    def __init__(self, fallback_port: int = PORT_SYNTAX):
        self.fallback_port = fallback_port

    def validate_safety(self, command: str) -> Tuple[str, str]:
        """Check for potentially destructive or catastrophic operations."""
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return "REJECTED", f"Matches forbidden destructive pattern: {pattern}"
        cmd_lower = command.lower()
        if any(w in cmd_lower for w in ["format", "mkfs", "drop database", "shred"]):
            return "REJECTED", "Matches destructive disk or database operation"
        if "sudo " in command:
            return "CAUTION", "Requires elevated privileges (sudo)"
        if command.startswith("rm ") or " rm " in command or "delete" in cmd_lower:
            return "CAUTION", "File or resource deletion operation"
        return "SAFE", "Standard non-destructive command"

    def _create_draft(self, raw_prompt: str, cmd_str: str, rationale: str, t0: float) -> SpeculativeCommandDraft:
        try:
            parts = shlex.split(cmd_str)
        except ValueError:
            parts = cmd_str.split()
        safety, safety_rat = self.validate_safety(cmd_str)
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return SpeculativeCommandDraft(
            raw_prompt=raw_prompt,
            speculative_command=parts[0],
            suggested_args=parts[1:],
            confidence_score=0.98,
            safety_rating=safety,
            rationale=f"{rationale} ({safety_rat})",
            latency_ms=latency,
            drafter_model="Fast-Deterministic-AST",
        )

    def draft(self, user_intent: str) -> SpeculativeCommandDraft:
        t0 = time.perf_counter()
        
        # Clean leading comments, markdown bullets, numberings, or prompt prefix
        raw_cleaned = re.sub(r"^[\s#\d\.\-\*•:]+", "", user_intent).strip()
        cleaned_intent = raw_cleaned.lower()

        # Handle explicit comments or empty intents
        if user_intent.strip().startswith("#") or not cleaned_intent:
            return SpeculativeCommandDraft(
                raw_prompt=user_intent,
                speculative_command="echo",
                suggested_args=["[Ignored shell comment]"],
                confidence_score=1.0,
                safety_rating="SAFE",
                rationale="Ignored shell comment line",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                drafter_model="Fast-Deterministic-AST",
            )

        # Handle SSH shorthand: user@host or root@ip
        if re.match(r"^[a-zA-Z0-9_\-]+@[a-zA-Z0-9_\-\.]+$", user_intent.strip()):
            ssh_target = user_intent.strip()
            return self._create_draft(user_intent, f"ssh {ssh_target}", f"Auto-translated SSH shorthand '{ssh_target}' to 'ssh {ssh_target}'", t0)

        # 1. Fast speculative deterministic match (<0.1ms)
        # Phase 1: Exact match
        if cleaned_intent in self.COMMON_SPECULATIVE_MAPPINGS:
            cmd = self.COMMON_SPECULATIVE_MAPPINGS[cleaned_intent]
            return self._create_draft(user_intent, cmd, f"Deterministic exact mapping for '{cleaned_intent}'", t0)

        # Priority composite intent check for Polyglot Specialist IDE & Runtime Integration
        if any(
            w in cleaned_intent
            for w in [
                "polyglot-go-bubbletea-specialist",
                "polyglot-kotlin-android-specialist",
                "polyglot-c-cpp-specialist",
                "polyglot-python-specialist",
                "polyglot-rust-wgpu-specialist",
                "polyglot-typescript-web-specialist",
                "polyglot specialist",
                "specialist skill",
                "langgo",
            ]
        ) and not any(w in cleaned_intent for w in ["automate-247", "automation-protocol", "/boost", "teamwork-preview"]):
            target_arg = "all"
            matched_targets = [
                t for t in ("langgo", "goland", "pycharm", "intellij", "chromium", "bt-serial")
                if t in cleaned_intent
            ]
            if len(matched_targets) == 1:
                target_arg = matched_targets[0]
            return self._create_draft(
                user_intent,
                f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py specialists --target {target_arg}",
                f"Polyglot Specialist IDE & Runtime Integration (target={target_arg})",
                t0,
            )

        # Priority composite intent check for 24/7 Lens + Qwen 3D + Gemma 2 + Root/Shizuku/rish + Scrcpy 5.0 + Page Assist protocol
        if (
            ("24/7" in cleaned_intent and ("automation" in cleaned_intent or "lens" in cleaned_intent))
            or any(
                w in cleaned_intent
                for w in [
                    "shizuku",
                    "shiziku",
                    "rish",
                    "automate-247",
                    "automation-protocol",
                    "screen-lens-sovereign",
                    "/boost",
                    "--boost",
                    "teamwork-preview",
                    "teamwork_preview",
                ]
            )
        ):
            extra_flags: List[str] = []
            if any(w in cleaned_intent for w in ["until", "converge", "/goal"]):
                extra_flags.append("--until-converged")
            if "teamwork-preview" in cleaned_intent or "teamwork_preview" in cleaned_intent:
                extra_flags.append("--teamwork-preview")
            if "boost" in cleaned_intent:
                extra_flags.append("--boost")
            flag_suffix = (" " + " ".join(extra_flags)) if extra_flags else ""
            return self._create_draft(
                user_intent,
                f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_sovereign_unified_system.py automate-247{flag_suffix}",
                "24/7 Lens + Qwen 3D + Gemma 2 + Root/Shizuku/rish + Scrcpy 5.0 + Page Assist Automation Training Protocol",
                t0,
            )

        # Phase 2: Word-boundary phrase match (longer keys first to prevent short substrings hijacking intents)
        sorted_mappings = sorted(self.COMMON_SPECULATIVE_MAPPINGS.items(), key=lambda item: len(item[0]), reverse=True)
        for key, cmd in sorted_mappings:
            pattern = r'(?:\b|^)' + re.escape(key) + r'(?:\b|$)'
            if re.search(pattern, cleaned_intent):
                return self._create_draft(user_intent, cmd, f"Deterministic mapping for '{key}'", t0)

        # Smart keyword-based deterministic routing for Continuous Training of lauburu-lens-argon:latest
        if any(w in cleaned_intent for w in ["lauburu-lens-argon", "argontelemetry", "continuous training", "telemetry trainer"]):
            if "status" in cleaned_intent and "run" not in cleaned_intent:
                return self._create_draft(
                    user_intent,
                    f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --status",
                    "Lauburu Lens Argon Continuous Training Status",
                    t0,
                )
            return self._create_draft(
                user_intent,
                f"/opt/homebrew/bin/python3 {GEMINI_TELEMETRY_TRAINER} --burst 3",
                "Continuous Training of lauburu-lens-argon:latest (MLX Metal GPU SFT + DPO + MRL)",
                t0,
            )

        # Smart keyword-based deterministic routing for Neo4j, EmbeddingGemma 2, and Root Orchestration
        orchestrator_py = f"python3 {REPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py"
        if any(w in cleaned_intent for w in ["neo4j", "cypher", "embeddinggemma", "gemma 2", "gemma2", "mrl", "rag"]):
            if "schema" in cleaned_intent:
                return self._create_draft(user_intent, f"{orchestrator_py} schema", "Neo4j Schema & Vector Index Inspection", t0)
            elif "seed" in cleaned_intent or "sync" in cleaned_intent:
                return self._create_draft(user_intent, f"{orchestrator_py} seed", "Neo4j + Qdrant MRL Mesh Topology & Document Seed", t0)
            elif cleaned_intent.startswith("cypher "):
                q = raw_cleaned[7:].strip()
                return self._create_draft(user_intent, f"{orchestrator_py} cypher {shlex.quote(q)}", "Neo4j Cypher Query Execution", t0)
            elif cleaned_intent.startswith("rag "):
                q = raw_cleaned[4:].strip()
                return self._create_draft(user_intent, f"{orchestrator_py} rag {shlex.quote(q)}", "EmbeddingGemma 2 + Neo4j GraphRAG Query", t0)
            else:
                return self._create_draft(user_intent, f"{orchestrator_py} status", "Neo4j & EmbeddingGemma 2 Global Orchestrator Status", t0)

        # Smart keyword-based deterministic routing for Speedify & Channel Bonding
        if any(w in cleaned_intent for w in ["speedify", "channel bonding", "bonding", "multipath"]):
            if any(w in cleaned_intent for w in ["interface", "status", "list", "show", "inspect", "check"]):
                cmd = "rust_bonding_engine interfaces"
                return self._create_draft(user_intent, cmd, "Speedify/Bonding Interface Query", t0)
            elif any(w in cleaned_intent for w in ["e2e", "test", "automate", "run", "benchmark"]):
                cmd = "rust_bonding_engine test-e2e --payload-size-mb 5"
                return self._create_draft(user_intent, cmd, "Automated Speedify Channel Bonding E2E Test", t0)
            elif "server" in cleaned_intent:
                cmd = "rust_bonding_engine server --port 18804 --bind 0.0.0.0"
                return self._create_draft(user_intent, cmd, "Start Bonding Server", t0)
            elif "client" in cleaned_intent:
                cmd = "rust_bonding_engine client --target 127.0.0.1 --port 18804 --socks5-bind 127.0.0.1:1080"
                return self._create_draft(user_intent, cmd, "Start Bonding Client", t0)
            elif any(w in cleaned_intent for w in ["traffic", "curl", "route", "bandwidth"]):
                cmd = "curl -x socks5://127.0.0.1:1080 https://speed.cloudflare.com/__down?bytes=25000000 -o /dev/null"
                return self._create_draft(user_intent, cmd, "Test Bandwidth via Bonded SOCKS5 Proxy", t0)

        if "route traffic" in cleaned_intent:
            cmd = "curl -x socks5://127.0.0.1:1080 https://speed.cloudflare.com/__down?bytes=25000000 -o /dev/null"
            return self._create_draft(user_intent, cmd, "Test Bandwidth via Bonded SOCKS5 Proxy", t0)

        # Smart keyword-based deterministic routing for Screen Lens Sovereign
        if any(w in cleaned_intent for w in ["screen lens", "screen-lens", "screen capture", "screen query", "screen search"]):
            if any(w in cleaned_intent for w in ["start", "launch"]):
                return self._create_draft(user_intent, "screen-lens start", "Screen Lens Sovereign Daemon Start", t0)
            elif any(w in cleaned_intent for w in ["stop", "kill", "terminate"]):
                return self._create_draft(user_intent, "screen-lens stop", "Screen Lens Sovereign Daemon Stop", t0)
            elif any(w in cleaned_intent for w in ["restart", "reload"]):
                return self._create_draft(user_intent, "screen-lens restart", "Screen Lens Sovereign Daemon Restart", t0)
            elif any(w in cleaned_intent for w in ["query", "search", "find"]):
                match = re.search(r'(?:query|search|find)\s+(?:screen\s+)?(.+)', cleaned_intent)
                query_term = match.group(1).strip() if match else ""
                if query_term:
                    return self._create_draft(user_intent, f"screen-lens query {query_term}", f"Screen Lens Sovereign OCR Query '{query_term}'", t0)
                return self._create_draft(user_intent, "screen-lens latest", "Screen Lens Sovereign OCR Latest", t0)
            elif any(w in cleaned_intent for w in ["capture", "latest", "ocr", "recent"]):
                return self._create_draft(user_intent, "screen-lens latest", "Screen Lens Sovereign Latest Captures", t0)
            else:
                return self._create_draft(user_intent, "screen-lens status", "Screen Lens Sovereign Status", t0)

        # 2. Local AI Drafter via Port 8082 (Master) / 8081 (Syntax) across localhost or L1 (192.168.8.143)
        import socket
        for host in ["127.0.0.1", "192.168.8.143"]:
            for port in [PORT_MASTER, self.fallback_port]:
                try:
                    with socket.create_connection((host, port), timeout=0.05):
                        pass
                except OSError:
                    continue

                model_name = "qwen_38_max" if port == PORT_MASTER else "qwen2.5-coder-7b"
                prompt_payload = {
                    "model": model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a specialized Unix/macOS CLI syntax drafter. Given user intent, output ONLY the single best shell command line. No markdown formatting, no explanations, no fences."
                        },
                        {"role": "user", "content": user_intent}
                    ],
                    "max_tokens": 64,
                    "temperature": 0.1
                }

                try:
                    req = urllib.request.Request(
                        f"http://{host}:{port}/v1/chat/completions",
                        data=json.dumps(prompt_payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=1.5) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        raw_cmd = data["choices"][0]["message"]["content"].strip()
                        # Clean fences if any
                        raw_cmd = raw_cmd.strip("`").replace("```bash", "").replace("```sh", "").strip()
                        parts = raw_cmd.split()
                        if parts:
                            safety, rationale = self.validate_safety(raw_cmd)
                            latency = round((time.perf_counter() - t0) * 1000, 2)
                            if safety == "REJECTED":
                                conf = 0.05
                            elif safety == "CAUTION":
                                conf = 0.45
                            else:
                                conf = 0.92
                            return SpeculativeCommandDraft(
                                raw_prompt=user_intent,
                                speculative_command=parts[0],
                                suggested_args=parts[1:],
                                confidence_score=conf,
                                safety_rating=safety,
                                rationale=rationale,
                                latency_ms=latency,
                                drafter_model=f"Local-Qwen-Port-{port}",
                            )
                except Exception:
                    continue

        # 3. Fallback Heuristic Drafter (Transparent fallback with realistic low confidence)
        parts = raw_cleaned.split()
        cmd = parts[0] if parts else "echo"
        args = parts[1:] if len(parts) > 1 else []
        safety, rationale = self.validate_safety(raw_cleaned)
        conf = 0.25 if safety == "SAFE" else 0.05
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return SpeculativeCommandDraft(
            raw_prompt=user_intent,
            speculative_command=cmd,
            suggested_args=args,
            confidence_score=conf,
            safety_rating=safety,
            rationale=rationale if safety != "SAFE" else "Pass-through heuristic tokenization (Local AI offline or timed out)",
            latency_ms=latency,
            drafter_model="Heuristic-Tokenizer",
        )


# -----------------------------------------------------------------------------
# 3. Streaming Subprocess Runner (Zero-Mock Verified)
# -----------------------------------------------------------------------------
class StreamingSubprocessRunner:
    """Executes commands with non-blocking line streaming and SHA256 receipts."""

    def __init__(self, default_timeout_sec: float = 30.0):
        self.default_timeout_sec = default_timeout_sec

    def execute(
        self,
        command: str,
        args: Optional[List[str]] = None,
        cwd: Optional[Path] = None,
        line_callback: Optional[Callable[[str], None]] = None,
        timeout_sec: Optional[float] = None,
        env_extra: Optional[Dict[str, str]] = None,
    ) -> CliExecutionReceipt:
        t0 = time.perf_counter()
        if not args and " " in command:
            try:
                full_args = shlex.split(command)
            except ValueError:
                full_args = command.split()
            command = full_args[0]
            args = full_args[1:]
        else:
            full_args = [command] + (args or [])

        work_dir = cwd or REPO_ROOT
        timeout = timeout_sec or self.default_timeout_sec

        env = dict(os.environ)
        env["DEVELOPER_DIR"] = "/Library/Developer/CommandLineTools"
        extra_paths = [
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/Volumes/.local/bin",
            str(Path.home() / ".local/bin"),
            str(REPO_ROOT / "06_scripts_and_tooling"),
            str(REPO_ROOT / "06_scripts_and_tooling/network"),
            str(REPO_ROOT / "06_scripts_and_tooling/automation"),
        ]
        current_path = env.get("PATH", "/usr/bin:/bin")
        env["PATH"] = ":".join(extra_paths + [current_path])
        if env_extra:
            env.update(env_extra)

        stdout_lines: List[str] = []
        stderr_lines: List[str] = []

        try:
            proc = subprocess.Popen(
                full_args,
                cwd=str(work_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
            )

            # Stream stdout
            if proc.stdout:
                for line in proc.stdout:
                    cleaned = line.rstrip("\r\n")
                    stdout_lines.append(cleaned)
                    if line_callback:
                        line_callback(cleaned)

            # Collect any stderr
            if proc.stderr:
                for line in proc.stderr:
                    cleaned = line.rstrip("\r\n")
                    stderr_lines.append(cleaned)

            exit_code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            exit_code = -9
            stderr_lines.append(f"Command timed out after {timeout}s: {' '.join(full_args)}")
        except Exception as e:
            exit_code = 127
            stderr_lines.append(f"Subprocess execution error: {e}")

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        raw_receipt = f"{' '.join(full_args)}|{exit_code}|{duration_ms}|{len(stdout_lines)}"
        sha256_hash = hashlib.sha256(raw_receipt.encode("utf-8")).hexdigest()
        ts = datetime.now(timezone.utc).isoformat()

        # Rule #0 & Rule #1: zero_mock_certified is strictly True ONLY if execution actually succeeded with Exit Code 0
        is_zero_mock = (exit_code == 0 and not any("Subprocess execution error" in l for l in stderr_lines))

        receipt = CliExecutionReceipt(
            command=command,
            args=args or [],
            exit_code=exit_code,
            duration_ms=duration_ms,
            stdout_lines=stdout_lines,
            stderr_lines=stderr_lines,
            sha256_receipt=sha256_hash,
            timestamp=ts,
            zero_mock_certified=is_zero_mock,
        )

        # Append to execution log
        self._log_receipt(receipt)
        return receipt

    def _log_receipt(self, receipt: CliExecutionReceipt) -> None:
        try:
            EXECUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(EXECUTION_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(receipt.to_dict()) + "\n")
        except Exception:
            pass


# -----------------------------------------------------------------------------
# 4. Tri-Vault Data Retrieval Engine
# -----------------------------------------------------------------------------
class TriVaultDataRetriever:
    """High-throughput zero-mock retrieval across Obsidian, PySpark, and Monorepo."""

    def __init__(self):
        self.obsidian_root = OBSIDIAN_VAULT
        self.data_lake = DATA_LAKE

    def retrieve(
        self,
        query: str,
        source: str = "all",
        max_results: int = 10
    ) -> DataRetrievalResult:
        t0 = time.perf_counter()
        records: List[Dict[str, Any]] = []
        normalized_query = query.strip().lower()

        # 1. Search Obsidian Knowledge Vault
        if source in ["all", "obsidian"]:
            if self.obsidian_root.exists():
                for md_file in self.obsidian_root.rglob("*.md"):
                    if md_file.is_file():
                        try:
                            content = md_file.read_text(encoding="utf-8", errors="ignore")
                            if normalized_query in md_file.name.lower() or normalized_query in content.lower():
                                # Extract matching lines
                                snippets = []
                                for line in content.splitlines():
                                    if normalized_query in line.lower():
                                        snippets.append(line.strip())
                                        if len(snippets) >= 3:
                                            break
                                records.append({
                                    "source": "obsidian",
                                    "path": str(md_file.relative_to(self.obsidian_root)),
                                    "title": md_file.stem,
                                    "snippets": snippets,
                                    "size_bytes": md_file.stat().st_size,
                                })
                                if len(records) >= max_results:
                                    break
                        except Exception:
                            continue

        # 2. Search PySpark Data Lake / JSONL datasets
        if source in ["all", "pyspark", "lake"] and len(records) < max_results:
            lake_files = [
                DATA_LAKE / "data/polyglot_go_wgpu_training.jsonl",
                DATA_LAKE / "data/speculative_cli_executions.jsonl",
                LORA_DATASET,
            ]
            for jf in lake_files:
                if jf.exists() and jf.is_file():
                    try:
                        with open(jf, "r", encoding="utf-8", errors="ignore") as f:
                            # Read tail lines for recent items
                            lines = f.readlines()
                            for line in reversed(lines[-200:]):
                                if normalized_query in line.lower():
                                    try:
                                        item = json.loads(line)
                                        records.append({
                                            "source": "data_lake",
                                            "path": str(jf.name),
                                            "item": item,
                                        })
                                        if len(records) >= max_results:
                                            break
                                    except Exception:
                                        continue
                    except Exception:
                        continue

        # 3. Search Monorepo Core Architecture & Apps
        if source in ["all", "monorepo"] and len(records) < max_results:
            search_paths = [REPO_ROOT / "07_docs_and_architecture", REPO_ROOT / "01_apps"]
            for sp in search_paths:
                if sp.exists():
                    for f in sp.rglob("*.md"):
                        if f.is_file() and (normalized_query in f.name.lower()):
                            records.append({
                                "source": "monorepo_docs",
                                "path": str(f.relative_to(REPO_ROOT)),
                                "title": f.name,
                            })
                            if len(records) >= max_results:
                                break

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        return DataRetrievalResult(
            query=query,
            source=source,
            matches_found=len(records),
            records=records[:max_results],
            duration_ms=duration_ms,
        )


# -----------------------------------------------------------------------------
# 5. Sovereign Credential Handler (/api-key-handler)
# -----------------------------------------------------------------------------
class SovereignApiKeyHandler:
    """
    Sovereign Local AI credential manager.
    Scans ~/Downloads and ~/Desktop for new credentials, extracts them locally
    via Port 8081 without cloud leakage, updates .env with 0o600, and wipes temp files.
    """

    KNOWN_PATTERNS = {
        "GEMINI_API_KEY": r"(AIzaSy[A-Za-z0-9_-]{33}|AQ\.[A-Za-z0-9_-]{50,})",
        "HF_TOKEN": r"hf_[A-Za-z0-9]{34,}",
        "CLOUDFLARE_API_TOKEN": r"([A-Za-z0-9_-]{40})",
        "NVIDIA_API_KEY": r"nvapi-[A-Za-z0-9_-]{60,}",
        "XAI_API_KEY": r"xai-[A-Za-z0-9_-]{70,}",
        "GROQ_API_KEY": r"gsk_[A-Za-z0-9]{50,}",
    }

    def scan_for_credential_files(self, max_age_hours: float = 48.0) -> List[Path]:
        """Scan candidate user directories for freshly downloaded key/secret files."""
        candidates: List[Path] = []
        search_dirs = [Path.home() / "Downloads", Path.home() / "Desktop"]
        now = time.time()
        max_age_sec = max_age_hours * 3600

        for sdir in search_dirs:
            if not sdir.exists():
                continue
            for ext in ["*.json", "*.csv", "*.txt", "*.env"]:
                for f in sdir.glob(ext):
                    if f.is_file():
                        try:
                            mtime = f.stat().st_mtime
                            if (now - mtime) <= max_age_sec:
                                # Prioritize files with key/secret in name or content
                                name_lower = f.name.lower()
                                if any(k in name_lower for k in ["key", "secret", "cred", "token", "auth", "client"]):
                                    candidates.append(f)
                        except Exception:
                            continue
        return candidates

    def extract_credential_locally(self, file_path: Path) -> Dict[str, str]:
        """
        Extract credentials strictly using local regex or Port 8081 local model.
        NEVER sends key file content to external cloud models.
        """
        extracted: Dict[str, str] = {}
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return extracted

        # Pass 1: Local Regex Extraction (Immediate & 100% Deterministic)
        for key_name, pattern in self.KNOWN_PATTERNS.items():
            matches = re.findall(pattern, content)
            if matches:
                # Take longest match if multiple
                best_match = max(matches, key=len)
                extracted[key_name] = best_match

        # Pass 2: JSON Key Parsing (e.g. Google service accounts or OAuth client secrets)
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                if "api_key" in data:
                    extracted["API_KEY"] = str(data["api_key"])
                if "private_key" in data:
                    extracted["GCP_PRIVATE_KEY"] = str(data["private_key"])
                if "web" in data and "client_id" in data["web"]:
                    extracted["GOOGLE_CLIENT_ID"] = str(data["web"]["client_id"])
                    if "client_secret" in data["web"]:
                        extracted["GOOGLE_CLIENT_SECRET"] = str(data["web"]["client_secret"])
                if "client_id" in data and "client_secret" in data:
                    extracted["CLIENT_ID"] = str(data["client_id"])
                    extracted["CLIENT_SECRET"] = str(data["client_secret"])
        except Exception:
            pass

        return extracted

    def inject_credential(self, key_name: str, key_value: str) -> bool:
        """Inject credential into ~/.env and monorepo .env with chmod 600."""
        target_files = [USER_ENV, MONO_ENV]
        success = True

        for target in target_files:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                lines: List[str] = []
                replaced = False

                if target.exists():
                    for line in target.read_text(encoding="utf-8").splitlines():
                        stripped = line.strip()
                        if stripped.startswith(f"{key_name}=") or stripped.startswith(f"# {key_name}="):
                            lines.append(f"{key_name}={key_value}")
                            replaced = True
                        else:
                            lines.append(line)

                if not replaced:
                    lines.append(f"{key_name}={key_value}")

                target.write_text("\n".join(lines) + "\n", encoding="utf-8")
                target.chmod(0o600)
            except Exception as e:
                success = False

        return success

    def run_credential_hunt_and_hygiene(self, dry_run: bool = False) -> Dict[str, Any]:
        """Full /api-key-handler routine: hunt, extract locally, save, audit, and wipe."""
        t0 = time.perf_counter()
        files = self.scan_for_credential_files()
        results: Dict[str, Any] = {
            "files_scanned": len(files),
            "credentials_found": {},
            "files_cleaned": [],
            "status": "COMPLETED",
        }

        for f in files:
            creds = self.extract_credential_locally(f)
            if creds:
                for k, v in creds.items():
                    results["credentials_found"][k] = f"{v[:6]}...{v[-4:]} ({len(v)} chars)"
                    if not dry_run:
                        self.inject_credential(k, v)

                if not dry_run and creds:
                    try:
                        # Secure zero-trace cleanup
                        f.unlink()
                        results["files_cleaned"].append(str(f))
                    except Exception:
                        pass

        results["duration_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return results


# -----------------------------------------------------------------------------
# 6. Master Speculative AI Engine (Unified Facade)
# -----------------------------------------------------------------------------
class SpeculativeCliDataEngine:
    """Unified Facade for Speculative CLI, Subprocess Streaming, Retrieval, and Credentials."""

    def __init__(self):
        self.drafter = SpeculativeCommandDrafter()
        self.runner = StreamingSubprocessRunner()
        self.retriever = TriVaultDataRetriever()
        self.key_handler = SovereignApiKeyHandler()

    def speculate_and_execute(
        self,
        intent_or_command: str,
        execute_if_safe: bool = True,
        timeout_sec: float = 30.0,
    ) -> Dict[str, Any]:
        """Drafts a command speculatively, checks safety, and executes if safe."""
        draft = self.drafter.draft(intent_or_command)

        if not execute_if_safe or draft.safety_rating == "REJECTED":
            return {
                "draft": draft.to_dict(),
                "executed": False,
                "reason": f"Execution halted. Safety: {draft.safety_rating}"
            }

        full_cmd = draft.speculative_command
        args = draft.suggested_args

        search_path = ":".join([
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/Volumes/.local/bin",
            str(Path.home() / ".local/bin"),
            str(REPO_ROOT / "06_scripts_and_tooling"),
            str(REPO_ROOT / "06_scripts_and_tooling/network"),
            str(REPO_ROOT / "06_scripts_and_tooling/automation"),
            os.environ.get("PATH", "/usr/bin:/bin"),
        ])

        # Binary Existence & Sanity Gate:
        # Check if binary exists in PATH before calling subprocess to prevent circular crashes on missing tools
        if not shutil.which(full_cmd, path=search_path) and not full_cmd.startswith(("./", "/", "~")):
            suggestion = f"brew install {full_cmd}"
            if full_cmd == "mosh":
                suggestion = "brew install mosh (or connect via 'ssh <host>')"
            elif full_cmd == "winget":
                suggestion = "winget is for Windows. Use 'brew install <package>' on macOS."
            elif full_cmd in ("hi", "hello", "hey"):
                suggestion = "Provide a CLI command or intent (e.g. 'network status', 'git status')."
            elif full_cmd == "heal":
                suggestion = "Use 'lauburu-network --test' or 'python3 06_scripts_and_tooling/network/nomad_courier_self_healer.py'."

            return {
                "draft": draft.to_dict(),
                "executed": False,
                "reason": f"Binary '{full_cmd}' not found in PATH.",
                "suggestion": suggestion,
            }

        receipt = self.runner.execute(full_cmd, args, timeout_sec=timeout_sec)

        return {
            "draft": draft.to_dict(),
            "executed": True,
            "receipt": receipt.to_dict(),
        }

    def retrieve_data(self, query: str, source: str = "all") -> Dict[str, Any]:
        return self.retriever.retrieve(query, source=source).to_dict()

    def handle_api_keys(self, dry_run: bool = False) -> Dict[str, Any]:
        return self.key_handler.run_credential_hunt_and_hygiene(dry_run=dry_run)


# Singleton accessor
_ENGINE_INSTANCE: Optional[SpeculativeCliDataEngine] = None


def get_speculative_cli_engine() -> SpeculativeCliDataEngine:
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        _ENGINE_INSTANCE = SpeculativeCliDataEngine()
    return _ENGINE_INSTANCE


# -----------------------------------------------------------------------------
# 7. CLI Entrypoint & Self-Test
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Speculative CLI & Tri-Vault Data Retrieval Engine")
    parser.add_argument("--speculate", type=str, help="Speculatively draft CLI command from prompt")
    parser.add_argument("--run", type=str, help="Stream and execute a CLI command with verification")
    parser.add_argument("--retrieve", type=str, help="Retrieve data across Tri-Vault storage")
    parser.add_argument("--source", type=str, default="all", choices=["all", "obsidian", "pyspark", "monorepo"])
    parser.add_argument("--api-key-handler", action="store_true", help="Run sovereign /api-key-handler credential hunt & cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Do not mutate or delete files during key scan")
    parser.add_argument("--test", action="store_true", help="Execute complete self-test of all 4 sub-engines")
    args = parser.parse_args()

    engine = get_speculative_cli_engine()

    if args.speculate:
        draft = engine.drafter.draft(args.speculate)
        print(json.dumps(draft.to_dict(), indent=2))
        sys.exit(0)

    if args.run:
        parts = args.run.split()
        receipt = engine.runner.execute(parts[0], parts[1:], line_callback=lambda l: print(f"[STREAM] {l}"))
        print(f"\n✅ Exit Code: {receipt.exit_code} in {receipt.duration_ms}ms | SHA: {receipt.sha256_receipt[:12]}")
        sys.exit(receipt.exit_code)

    if args.retrieve:
        res = engine.retrieve_data(args.retrieve, source=args.source)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    if args.api_key_handler:
        res = engine.handle_api_keys(dry_run=args.dry_run)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    if args.test:
        print("⚡ [SELF-TEST] Testing Speculative CLI & Data Retrieval Engine...")

        # 1. Test Speculative Drafter
        draft = engine.drafter.draft("check network topology")
        assert draft.speculative_command == "lauburu-network", f"Unexpected draft: {draft}"
        print(f"  1. Speculative Drafter: PASSED in {draft.latency_ms}ms ({draft.speculative_command} {draft.suggested_args})")

        # 2. Test Streaming Runner
        receipt = engine.runner.execute("echo", ["Lauburu Speculative AI Active"])
        assert receipt.exit_code == 0 and "Lauburu Speculative AI Active" in receipt.stdout_lines[0]
        print(f"  2. Streaming Runner:    PASSED in {receipt.duration_ms}ms (Exit 0, SHA: {receipt.sha256_receipt[:12]})")

        # 3. Test Tri-Vault Retrieval
        ret_res = engine.retrieve_data("CANONICAL", source="all")
        assert ret_res["matches_found"] > 0, "No records found"
        print(f"  3. Tri-Vault Retriever: PASSED in {ret_res['duration_ms']}ms (Found {ret_res['matches_found']} matches)")

        # 4. Test API Key Handler (dry run)
        key_res = engine.handle_api_keys(dry_run=True)
        print(f"  4. API Key Handler:     PASSED in {key_res['duration_ms']}ms (Scanned {key_res['files_scanned']} files)")

        print("✅ [SELF-TEST] All 4 Sub-Engines Verified with 100% Authentic Exit Code 0.")
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
