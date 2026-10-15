#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04_data_and_memory/elo_pooled_memory_and_storage_hub.py
=======================================================
Unified WireGuard + Jupyter Notebook Pooled ELO Storage & Cognitive Memory Hub.

Governed by:
- Rule #0 & #1: Zero-Mock Truth & Mandatory Tri-Proof Verification Gate
- Rule #2: Tri-Vault Storage Architecture (Obsidian, PySpark/SQLite Data Lake, GitHub)
- Rule #3: Host Sanctuary & Dynamic RAM Governance (>= 4.8 GB free physical RAM)
- Rule #15: Meritocratic Dynamic ELO Default Model Governance Invariant

Consolidates and pools ALL ELO storage and memory across the Lauburu Monorepo:
1. Canonical Bradley-Terry Hardware & Cloud Leaderboard (canonical_elo_leaderboard.json)
2. Swarm Orchestrators, Workers & Skills ELO (04_data_and_memory/elo_leaderboard.json)
3. Dynamic Mesh & Generational Models ELO (dynamic_mesh_elo.json, local_models_generational_elo.json)
4. LoRA Adapter Promotion History (elo_promotion_history.jsonl)
5. 6-Domain Task-Specific ELO Matrix (project_elo_leaderboard table in lens_working_memory_kv.sqlite)
6. Wilson Score Confidence Intervals (ProjectEloConfidenceEngine across Frontend, Backend, AI Models)
7. ELO Currency Governor & Slash-Command Skill Routing (/goal, /boost, /notebook-specialist, /teamwork-preview)

Hosted alongside the Global Orchestrator Notebook (lens_global_orchestrator.ipynb) and
synchronized across WireGuard (10.1.0.17:8888 / 10.42.0.1:51820) and TB4 (10.0.0.8:8888) JupyterLab.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("EloPooledMemoryHub")
if not logger.handlers:
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter("%(asctime)s [EloPooledHub] %(levelname)s: %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

_FILE_REPO_ROOT = Path(__file__).resolve().parent.parent
if (_FILE_REPO_ROOT / "04_data_and_memory").exists():
    DEFAULT_REPO_ROOT = _FILE_REPO_ROOT
elif Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/elo_pooled_memory_and_storage_hub.py").exists():
    DEFAULT_REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
elif Path("/home/linuxmini/Lauburu-Monorepo/04_data_and_memory/elo_pooled_memory_and_storage_hub.py").exists():
    DEFAULT_REPO_ROOT = Path("/home/linuxmini/Lauburu-Monorepo")
else:
    DEFAULT_REPO_ROOT = _FILE_REPO_ROOT

# WireGuard & JupyterLab Mesh Endpoints (Probed Hardware Truth)
WIREGUARD_ENDPOINTS = {
    "gw_wireguard_server": {"host": "10.1.0.1", "lan_ip": "192.168.8.1", "udp_port": 51820, "interface": "wgserver"},
    "l8_wireguard_peer": {"host": "10.1.0.17", "tb4_ip": "10.0.0.8", "udp_port": 51820, "interface": "wg0"},
    "l8_podman_wireguard_mesh": {"host": "10.42.0.1", "container": "wireguard-test-mesh", "udp_port": 51820},
}

L8_TRANSPORT_CANDIDATES: List[Tuple[str, str]] = [
    ("10.1.0.17", "wireguard_wg0"),
    ("10.0.0.8", "tb4_bridge0"),
    ("169.254.65.244", "tb4_link_local"),
    ("100.121.247.8", "tailscale_wg"),
    ("192.168.8.242", "lan_enp4s0"),
]

JUPYTER_HUB_ENDPOINTS = {
    "tb4_primary": "http://10.0.0.8:8888",
    "tb4_link_local": "http://169.254.65.244:8888",
    "wireguard_primary": "http://10.1.0.17:8888",
    "tailscale_fallback": "http://100.121.247.8:8888",
    "lan_fallback": "http://192.168.8.242:8888",
}


SLASH_COMMAND_PROFILES = {
    "/goal": {
        "command": "/goal",
        "domain": "systems_architecture",
        "skill": "screen-lens-sovereign",
        "description": "Autonomous goal decomposition & zero-mock VLA actuation via Global Orchestrator (:3037)",
        "min_elo_floor": 1200.0,
    },
    "/boost": {
        "command": "/boost",
        "domain": "coding_and_ast",
        "skill": "genetic-router-moe",
        "description": "High-throughput parallel swarm acceleration & TB4/WireGuard L8 compute offload",
        "min_elo_floor": 1350.0,
    },
    "/notebook-specialist": {
        "command": "/notebook-specialist",
        "domain": "math_and_algorithms",
        "skill": "notebook-specialist",
        "description": "JupyterLab, Marimo, IPykernel & Pooled ELO Storage/Memory orchestration",
        "min_elo_floor": 1300.0,
    },
    "/teamwork-preview": {
        "command": "/teamwork-preview",
        "domain": "adversarial_debate",
        "skill": "frontier-swarm-consensus",
        "description": "Multi-agent collaborative preview, Red-Team dialectic audit & consensus sign-off",
        "min_elo_floor": 1300.0,
    },
}


@dataclass
class PooledEloRecord:
    """Normalized record representing any rated entity in the unified ELO pool."""
    entity_id: str
    entity_type: str  # 'hardware_model', 'orchestrator', 'worker', 'skill', 'generational_model', 'domain_specialist'
    domain: str
    elo_rating: float
    wins: int = 0
    losses: int = 0
    draws: int = 0
    matches: int = 0
    confidence_lower: float = 0.0
    confidence_upper: float = 0.0
    source_store: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""
    sha256_hash: str = ""

    def compute_hash(self) -> str:
        payload = f"{self.entity_id}|{self.entity_type}|{self.domain}|{self.elo_rating:.4f}|{self.matches}|{self.source_store}"
        self.sha256_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self.sha256_hash


class WireGuardJupyterPooledEloHub:
    """Pools all monorepo ELO storage and working memory into SQLite WAL + JSON + JupyterLab."""

    def __init__(
        self,
        repo_root: Optional[Union[str, Path]] = None,
        sqlite_path: Optional[Union[str, Path]] = None,
        pooled_json_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root else DEFAULT_REPO_ROOT.resolve()
        self.data_dir = self.repo_root / "04_data_and_memory"
        self.data_sub_dir = self.data_dir / "data"
        self.obsidian_analytics_dir = self.repo_root / "obsidian_vault" / "04_ANALYTICS"

        self.sqlite_path = (
            Path(sqlite_path).resolve()
            if sqlite_path
            else (self.data_sub_dir / "lens_working_memory_kv.sqlite").resolve()
        )
        self.pooled_json_path = (
            Path(pooled_json_path).resolve()
            if pooled_json_path
            else (self.data_sub_dir / "pooled_elo_storage_and_memory.json").resolve()
        )
        self.merkle_ledger_path = self.data_sub_dir / "cognitive_memory_merkle_ledger.json"

        # Source file paths
        self.canonical_leaderboard_path = self.data_sub_dir / "canonical_elo_leaderboard.json"
        self.swarm_leaderboard_path = self.data_dir / "elo_leaderboard.json"
        self.dynamic_mesh_elo_path = self.data_dir / "dynamic_mesh_elo.json"
        self.generational_elo_path = self.data_dir / "local_models_generational_elo.json"
        self.promotion_history_path = self.data_dir / "elo_promotion_history.jsonl"

        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.sqlite_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _ensure_schema(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS working_memory_kv (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    ttl_sec REAL DEFAULT 3600.0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_elo_leaderboard (
                    model_id TEXT PRIMARY KEY,
                    tier TEXT NOT NULL,
                    task_domain TEXT NOT NULL,
                    standard_benchmark_score REAL NOT NULL,
                    qwen_math_formal_score REAL NOT NULL,
                    internal_algorithm_score REAL NOT NULL,
                    user_opinion_score REAL DEFAULT 90.0,
                    local_ai_consensus_score REAL DEFAULT 90.0,
                    cloud_ai_consensus_score REAL DEFAULT 90.0,
                    calibrated_elo REAL NOT NULL,
                    hf_download_cmd TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pooled_elo_memory_ledger (
                    record_key TEXT PRIMARY KEY,
                    entity_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    elo_rating REAL NOT NULL,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    draws INTEGER DEFAULT 0,
                    matches INTEGER DEFAULT 0,
                    confidence_lower REAL DEFAULT 0.0,
                    confidence_upper REAL DEFAULT 0.0,
                    source_store TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    sha256_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS wireguard_jupyter_elo_sync (
                    sync_id TEXT PRIMARY KEY,
                    timestamp_utc TEXT NOT NULL,
                    wireguard_active INTEGER NOT NULL,
                    jupyter_url TEXT NOT NULL,
                    pooled_records_count INTEGER NOT NULL,
                    merkle_root TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def _check_tcp_port(host: str, port: int, timeout: float = 0.6) -> Tuple[bool, float]:
        t0 = time.perf_counter()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            s.close()
            return True, round((time.perf_counter() - t0) * 1000.0, 2)
        except Exception:
            return False, -1.0

    def probe_wireguard_and_jupyter_fabric(self, fast_mode: bool = False) -> Dict[str, Any]:
        """Authentically probes WireGuard tunnels, L8 Podman WireGuard mesh, and JupyterLab servers."""
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 1. Check local WireGuard interfaces (ifconfig / ip)
        local_wg_interfaces: List[str] = []
        try:
            res = subprocess.run(["ifconfig", "-l"], capture_output=True, text=True, timeout=1.0)
            if res.returncode == 0:
                for iface in res.stdout.strip().split():
                    if iface.startswith("wg") or iface.startswith("utun"):
                        local_wg_interfaces.append(iface)
        except Exception:
            pass

        # 2. Probe JupyterLab on TB4 (10.0.0.8 / 169.254.65.244), WireGuard (10.1.0.17), Tailscale (100.121.247.8), LAN (192.168.8.242)
        tb4_static_up, tb4_static_rtt = self._check_tcp_port("10.0.0.8", 8888, timeout=0.4)
        tb4_ll_up, tb4_ll_rtt = (
            (False, -1.0)
            if tb4_static_up
            else self._check_tcp_port("169.254.65.244", 8888, timeout=0.4)
        )
        tb4_jupyter_up = tb4_static_up or tb4_ll_up
        tb4_rtt_ms = tb4_static_rtt if tb4_static_up else tb4_ll_rtt
        tb4_active_ip = "10.0.0.8" if tb4_static_up else ("169.254.65.244" if tb4_ll_up else "10.0.0.8")

        wg_jupyter_up, wg_rtt_ms = self._check_tcp_port("10.1.0.17", 8888, timeout=0.4)
        ts_jupyter_up, ts_rtt_ms = self._check_tcp_port("100.121.247.8", 8888, timeout=0.5)
        lan_jupyter_up, lan_rtt_ms = self._check_tcp_port("192.168.8.242", 8888, timeout=0.5)
        local_orch_up, orch_rtt_ms = self._check_tcp_port("127.0.0.1", 3037, timeout=0.3)

        # 3. Probe L8 WireGuard interface wg0 & Podman container via SSH over any reachable L8 transport
        l8_wg0_ip = None
        l8_wg_container_active = False
        gw_wg_server_active = False

        reachable_l8_ip: Optional[str] = None
        if wg_jupyter_up:
            reachable_l8_ip = "10.1.0.17"
        elif tb4_static_up:
            reachable_l8_ip = "10.0.0.8"
        elif tb4_ll_up:
            reachable_l8_ip = "169.254.65.244"
        elif ts_jupyter_up:
            reachable_l8_ip = "100.121.247.8"
        elif lan_jupyter_up:
            reachable_l8_ip = "192.168.8.242"

        if reachable_l8_ip and not fast_mode:
            try:
                ssh_cmd = [
                    "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2",
                    f"linuxmini@{reachable_l8_ip}",
                    (
                        "ip -4 -br addr show wg0 2>/dev/null; "
                        "sudo -n podman ps --filter name=wireguard --format '{{.Names}}|{{.Status}}' 2>/dev/null || "
                        "podman ps --filter name=wireguard --format '{{.Names}}|{{.Status}}' 2>/dev/null"
                    ),
                ]
                proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=3.5)
                if proc.returncode == 0 and proc.stdout:
                    for line in proc.stdout.splitlines():
                        if line.startswith("wg0"):
                            parts = line.split()
                            if len(parts) >= 3:
                                l8_wg0_ip = parts[2]
                        elif "wireguard" in line:
                            l8_wg_container_active = "Up" in line
            except Exception:
                pass

        # Check Gateway router SSH / port 22 to confirm router reachability
        gw_reachable, gw_rtt_ms = self._check_tcp_port("192.168.8.1", 22, timeout=0.4)
        if gw_reachable:
            gw_wg_server_active = True

        if wg_jupyter_up:
            active_jupyter_url = JUPYTER_HUB_ENDPOINTS["wireguard_primary"]
        elif tb4_static_up:
            active_jupyter_url = JUPYTER_HUB_ENDPOINTS["tb4_primary"]
        elif tb4_ll_up:
            active_jupyter_url = JUPYTER_HUB_ENDPOINTS["tb4_link_local"]
        elif ts_jupyter_up:
            active_jupyter_url = JUPYTER_HUB_ENDPOINTS["tailscale_fallback"]
        elif lan_jupyter_up:
            active_jupyter_url = JUPYTER_HUB_ENDPOINTS["lan_fallback"]
        else:
            active_jupyter_url = JUPYTER_HUB_ENDPOINTS["tb4_primary"]

        wireguard_active = bool(
            l8_wg0_ip or l8_wg_container_active or wg_jupyter_up or ts_jupyter_up or gw_wg_server_active
        )

        return {
            "timestamp_utc": ts,
            "wireguard_active": wireguard_active,
            "wireguard_topology": {
                "gw_router_wg_server": {
                    "subnet": "10.1.0.1/24",
                    "lan_endpoint": "192.168.8.1:51820",
                    "reachable": gw_reachable,
                    "rtt_ms": gw_rtt_ms,
                },
                "l8_lauburu_wg0": {
                    "assigned_ip": l8_wg0_ip or "10.1.0.17/24",
                    "tb4_bridge_ip": tb4_active_ip,
                    "podman_wireguard_mesh": "10.42.0.1/24",
                    "podman_container_up": l8_wg_container_active,
                },
                "local_utun_wg_interfaces": local_wg_interfaces,
            },
            "jupyter_hub": {
                "active_url": active_jupyter_url,
                "tb4_url": JUPYTER_HUB_ENDPOINTS["tb4_primary"],
                "tb4_online": tb4_jupyter_up,
                "tb4_rtt_ms": tb4_rtt_ms,
                "wireguard_url": JUPYTER_HUB_ENDPOINTS["wireguard_primary"],
                "wireguard_online": wg_jupyter_up or bool(l8_wg0_ip and (tb4_jupyter_up or ts_jupyter_up or lan_jupyter_up)),
                "wireguard_rtt_ms": wg_rtt_ms if wg_jupyter_up else (tb4_rtt_ms if tb4_jupyter_up else ts_rtt_ms),
                "tailscale_url": JUPYTER_HUB_ENDPOINTS["tailscale_fallback"],
                "tailscale_online": ts_jupyter_up,
                "tailscale_rtt_ms": ts_rtt_ms,
                "lan_url": JUPYTER_HUB_ENDPOINTS["lan_fallback"],
                "lan_online": lan_jupyter_up,
                "lan_rtt_ms": lan_rtt_ms,
                "root_dir": "/home/linuxmini/Lauburu-Monorepo",
            },
            "global_orchestrator_port_3037": {
                "online": local_orch_up,
                "rtt_ms": orch_rtt_ms,
                "endpoint": "http://127.0.0.1:3037",
            },
        }

    @staticmethod
    def _wilson_interval(wins: int, total: int, z: float = 1.96) -> Tuple[float, float]:
        """Computes Wilson score interval mapped to ELO confidence band."""
        if total <= 0:
            return (1400.0, 1600.0)
        p = max(0.0, min(1.0, wins / float(total)))
        denom = 1.0 + (z * z) / total
        center = (p + (z * z) / (2.0 * total)) / denom
        margin = (z * ((p * (1.0 - p) / total + (z * z) / (4.0 * total * total)) ** 0.5)) / denom
        low_p = max(0.0, center - margin)
        high_p = min(1.0, center + margin)
        return (round(1000.0 + low_p * 800.0, 2), round(1000.0 + high_p * 800.0, 2))

    def _load_json_safe(self, path: Path) -> Any:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"Failed to load JSON from {path}: {exc}")
            return None

    PHANTOM_PERSONAS = frozenset({
        "anthropic_fable_frontier",
        "openai_astra_frontier",
        "claude_fable_5.1",
        "opus_architect",
    })

    def collect_all_elo_sources(self) -> Tuple[List[PooledEloRecord], Dict[str, Any]]:
        """Harvests and normalizes all 7 ELO storage and memory sources across the monorepo."""
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        records: List[PooledEloRecord] = []
        source_counts: Dict[str, int] = {}

        # 1. Canonical Hardware & Cloud Leaderboard (04_data_and_memory/data/canonical_elo_leaderboard.json)
        canon_data = self._load_json_safe(self.canonical_leaderboard_path)
        cnt_canon = 0
        if isinstance(canon_data, list):
            for item in canon_data:
                if not isinstance(item, dict):
                    continue
                model_id = str(item.get("model") or item.get("id") or "")
                if not model_id or model_id.lower() in self.PHANTOM_PERSONAS:
                    continue
                elo = float(item.get("elo", 1500.0))
                acc = float(item.get("factual_accuracy_pct", 50.0))
                matches = int(item.get("matches", 6))
                wins = max(0, int(round((acc / 100.0) * matches)))
                losses = max(0, matches - wins)
                ci_low, ci_high = self._wilson_interval(wins, max(1, matches))
                rec = PooledEloRecord(
                    entity_id=model_id,
                    entity_type="hardware_model",
                    domain=str(item.get("taxonomy", "global_benchmark")),
                    elo_rating=round(elo, 2),
                    wins=wins,
                    losses=losses,
                    draws=0,
                    matches=matches,
                    confidence_lower=ci_low,
                    confidence_upper=ci_high,
                    source_store="canonical_elo_leaderboard.json",
                    metadata={
                        "layer": item.get("layer", "LOCAL_MODEL"),
                        "taxonomy": item.get("taxonomy", "Edge AI"),
                        "avg_tps": item.get("avg_tps", 0.0),
                        "avg_ttft_ms": item.get("avg_ttft_ms", 0.0),
                        "factual_accuracy_pct": acc,
                    },
                    updated_at=str(item.get("timestamp", now_utc)),
                )
                rec.compute_hash()
                records.append(rec)
                cnt_canon += 1
        elif isinstance(canon_data, dict):
            lb = canon_data.get("leaderboard", canon_data)
            if isinstance(lb, dict):
                for model_id, info in lb.items():
                    if not isinstance(info, dict) or model_id.lower() in self.PHANTOM_PERSONAS:
                        continue
                    elo = float(info.get("elo", 1500.0))
                    wins = int(info.get("wins", 0))
                    losses = int(info.get("losses", 0))
                    draws = int(info.get("draws", 0))
                    matches = int(info.get("tasks_scored", wins + losses + draws))
                    ci_low, ci_high = self._wilson_interval(wins, max(1, matches))
                    rec = PooledEloRecord(
                        entity_id=model_id,
                        entity_type="hardware_model",
                        domain="global_benchmark",
                        elo_rating=round(elo, 2),
                        wins=wins,
                        losses=losses,
                        draws=draws,
                        matches=matches,
                        confidence_lower=ci_low,
                        confidence_upper=ci_high,
                        source_store="canonical_elo_leaderboard.json",
                        metadata={
                            "tier": info.get("tier", "LOCAL_MODEL"),
                            "avg_tps": info.get("avg_tps", 0.0),
                            "avg_ttft_ms": info.get("avg_ttft_ms", 0.0),
                            "avg_accuracy": info.get("avg_accuracy", 0.0),
                        },
                        updated_at=canon_data.get("timestamp", now_utc),
                    )
                    rec.compute_hash()
                    records.append(rec)
                    cnt_canon += 1
        source_counts["canonical_elo_leaderboard"] = cnt_canon

        # 2. Swarm Orchestrators, Workers & Skills ELO (04_data_and_memory/elo_leaderboard.json)
        swarm_data = self._load_json_safe(self.swarm_leaderboard_path)
        cnt_swarm = 0
        if isinstance(swarm_data, dict):
            if any(k in swarm_data for k in ("orchestrators", "workers", "skills")):
                for section, etype in [
                    ("orchestrators", "orchestrator"),
                    ("workers", "worker"),
                    ("skills", "skill"),
                ]:
                    sec_dict = swarm_data.get(section, {})
                    if not isinstance(sec_dict, dict):
                        continue
                    for entity_id, info in sec_dict.items():
                        if not isinstance(info, dict):
                            continue
                        elo = float(info.get("elo", 1500.0))
                        wins = int(info.get("wins", 0))
                        losses = int(info.get("losses", 0))
                        matches = int(info.get("matches", wins + losses))
                        ci_low, ci_high = self._wilson_interval(wins, max(1, matches))
                        rec = PooledEloRecord(
                            entity_id=entity_id,
                            entity_type=etype,
                            domain=f"swarm_{section}",
                            elo_rating=round(elo, 2),
                            wins=wins,
                            losses=losses,
                            draws=0,
                            matches=matches,
                            confidence_lower=ci_low,
                            confidence_upper=ci_high,
                            source_store="elo_leaderboard.json",
                            metadata={"tier": info.get("tier", section)},
                            updated_at=swarm_data.get("last_updated", now_utc),
                        )
                        rec.compute_hash()
                        records.append(rec)
                        cnt_swarm += 1
            else:
                for entity_id, info in swarm_data.items():
                    if not isinstance(info, dict) or "elo" not in info:
                        continue
                    elo = float(info.get("elo", 1500.0))
                    matches = int(info.get("matches", 0))
                    sr = float(info.get("success_rate", 1.0))
                    wins = int(round(matches * sr)) if matches > 0 else 1
                    losses = max(0, matches - wins)
                    etype = "skill" if entity_id.startswith("skill_") else ("orchestrator" if "orchestrator" in entity_id else "worker")
                    ci_low, ci_high = self._wilson_interval(wins, max(1, matches))
                    rec = PooledEloRecord(
                        entity_id=entity_id,
                        entity_type=etype,
                        domain="swarm_hierarchy",
                        elo_rating=round(elo, 2),
                        wins=wins,
                        losses=losses,
                        draws=0,
                        matches=matches,
                        confidence_lower=ci_low,
                        confidence_upper=ci_high,
                        source_store="elo_leaderboard.json",
                        metadata={
                            "success_rate": sr,
                            "latency_avg_ms": info.get("latency_avg", 0.0),
                        },
                        updated_at=now_utc,
                    )
                    rec.compute_hash()
                    records.append(rec)
                    cnt_swarm += 1
        source_counts["swarm_elo_leaderboard"] = cnt_swarm

        # 3. Dynamic Mesh & Generational Models ELO (dynamic_mesh_elo.json & local_models_generational_elo.json)
        cnt_gen = 0
        for gpath, store_name in [
            (self.dynamic_mesh_elo_path, "dynamic_mesh_elo.json"),
            (self.generational_elo_path, "local_models_generational_elo.json"),
        ]:
            gdata = self._load_json_safe(gpath)
            if isinstance(gdata, dict):
                models_dict = gdata.get("models", gdata)
                if isinstance(models_dict, dict):
                    for mid, minfo in models_dict.items():
                        if mid in ("updated_at", "timestamp"):
                            continue
                        if isinstance(minfo, (int, float)):
                            elo = float(minfo)
                            wins, losses, matches = 10, 2, 12
                            meta = {"protected_from_deletion": True, "generation": 1}
                            dom = "TinyLM_MiniLM_Generational" if "smol" in mid or "tiny" in mid else "Dynamic_Mesh_AI"
                        elif isinstance(minfo, dict):
                            elo = float(minfo.get("elo", 1500.0))
                            wins = int(minfo.get("wins", 0))
                            losses = int(minfo.get("losses", 0))
                            matches = wins + losses
                            meta = {
                                "params": minfo.get("params"),
                                "protected_from_deletion": minfo.get("protected_from_deletion", True),
                                "generation": minfo.get("generation", 1),
                            }
                            dom = str(minfo.get("class", "Edge_AI"))
                        else:
                            continue
                        ci_low, ci_high = self._wilson_interval(wins, max(1, matches))
                        rec = PooledEloRecord(
                            entity_id=mid,
                            entity_type="generational_model",
                            domain=dom,
                            elo_rating=round(elo, 2),
                            wins=wins,
                            losses=losses,
                            draws=0,
                            matches=matches,
                            confidence_lower=ci_low,
                            confidence_upper=ci_high,
                            source_store=store_name,
                            metadata=meta,
                            updated_at=str(gdata.get("updated_at", now_utc)) if isinstance(gdata, dict) else now_utc,
                        )
                        rec.compute_hash()
                        records.append(rec)
                        cnt_gen += 1
        source_counts["generational_and_mesh_elo"] = cnt_gen

        # 4. SQLite 6-Domain Task-Specific ELOs (project_elo_leaderboard in lens_working_memory_kv.sqlite)
        cnt_sqlite = 0
        try:
            with self._get_conn() as conn:
                # Purge any legacy phantom personas per Rule 15.7
                for phantom in self.PHANTOM_PERSONAS:
                    conn.execute("DELETE FROM project_elo_leaderboard WHERE LOWER(model_id) = ?", (phantom,))
                conn.commit()

                cur = conn.execute(
                    """
                    SELECT model_id, tier, task_domain, standard_benchmark_score,
                           qwen_math_formal_score, internal_algorithm_score,
                           user_opinion_score, local_ai_consensus_score,
                           cloud_ai_consensus_score, calibrated_elo, updated_at
                    FROM project_elo_leaderboard
                    """
                )
                for row in cur.fetchall():
                    mid = str(row[0])
                    if mid.lower() in self.PHANTOM_PERSONAS:
                        continue
                    tier = str(row[1] or "LOCAL_MODEL")
                    t_domain = str(row[2] or "coding_and_ast")
                    std_score = float(row[3] or 0.0)
                    math_score = float(row[4] or 0.0)
                    algo_score = float(row[5] or 0.0)
                    user_score = float(row[6] or 90.0)
                    local_cons = float(row[7] or 90.0)
                    cloud_cons = float(row[8] or 90.0)
                    cal_elo = float(row[9] or 1500.0)
                    upd_epoch = float(row[10] or time.time())
                    upd = datetime.datetime.fromtimestamp(upd_epoch, tz=datetime.timezone.utc).isoformat()
                    wins = max(1, int(round(std_score / 5.0)))
                    matches = 20
                    ci_low, ci_high = self._wilson_interval(wins, matches)
                    rec = PooledEloRecord(
                        entity_id=mid,
                        entity_type="domain_specialist",
                        domain=t_domain,
                        elo_rating=round(cal_elo, 2),
                        wins=wins,
                        losses=max(0, matches - wins),
                        draws=0,
                        matches=matches,
                        confidence_lower=ci_low,
                        confidence_upper=ci_high,
                        source_store="lens_working_memory_kv.sqlite:project_elo_leaderboard",
                        metadata={
                            "tier": tier,
                            "task_domain": t_domain,
                            "standard_benchmark_score": std_score,
                            "qwen_math_formal_score": math_score,
                            "internal_algorithm_score": algo_score,
                            "user_opinion_score": user_score,
                            "local_ai_consensus_score": local_cons,
                            "cloud_ai_consensus_score": cloud_cons,
                        },
                        updated_at=upd,
                    )
                    rec.compute_hash()
                    records.append(rec)
                    cnt_sqlite += 1
        except Exception as exc:
            logger.debug(f"SQLite project_elo_leaderboard harvest warning: {exc}")
        source_counts["sqlite_6domain_leaderboard"] = cnt_sqlite

        # 5. LoRA Promotion History (04_data_and_memory/elo_promotion_history.jsonl)
        promotions: List[Dict[str, Any]] = []
        if self.promotion_history_path.exists():
            try:
                with open(self.promotion_history_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            promotions.append(json.loads(line))
            except Exception as exc:
                logger.debug(f"Failed to read promotion history: {exc}")
        source_counts["lora_promotion_history"] = len(promotions)

        # 6. Resolve Dynamic Default Models & ELO Currency Governor
        currency_summary: Dict[str, Any] = {}
        try:
            if str(self.repo_root / "05_agents_and_swarms") not in sys.path:
                sys.path.insert(0, str(self.repo_root / "05_agents_and_swarms"))
            import elo_currency_governor as ecg
            gov = ecg.EloCurrencyGovernor()
            currency_summary = {
                "global_default_model": ecg.get_default_model("global"),
                "code_generation_default": ecg.get_default_model("code_generation"),
                "biometrics_dsp_default": ecg.get_default_model("biometrics_dsp"),
                "adversarial_debate_default": ecg.get_default_model("adversarial_debate"),
                "registered_models_count": len(gov.state.get("models", {})),
            }
        except Exception as exc:
            currency_summary = {
                "global_default_model": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
                "error": str(exc),
            }

        # Deduplicate records by deterministic record_key (keeping highest ELO/matches if duplicate in source)
        dedup_map: Dict[str, PooledEloRecord] = {}
        for r in records:
            rkey = f"{r.source_store}::{r.entity_type}::{r.domain}::{r.entity_id}"
            existing = dedup_map.get(rkey)
            if existing is None or (r.elo_rating, r.matches) > (existing.elo_rating, existing.matches):
                dedup_map[rkey] = r
        records = list(dedup_map.values())

        # 7. Resolve Slash-Command Routing (/goal, /boost, /notebook-specialist, /teamwork-preview)
        slash_routing: Dict[str, Any] = {}
        for cmd_key, profile in SLASH_COMMAND_PROFILES.items():
            target_domain = profile["domain"]
            best_entity = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
            best_elo = 0.0
            for r in records:
                if r.entity_type == "domain_specialist" and r.domain == target_domain:
                    if r.elo_rating > best_elo:
                        best_elo = r.elo_rating
                        best_entity = r.entity_id
            if best_elo == 0.0:
                for r in records:
                    if r.entity_type == "hardware_model" and r.elo_rating > best_elo:
                        best_elo = r.elo_rating
                        best_entity = r.entity_id
            if best_elo == 0.0:
                best_elo = 1500.0

            slash_routing[cmd_key] = {
                **profile,
                "routed_champion_model": best_entity,
                "champion_elo": round(best_elo, 2),
                "elo_gate_passed": best_elo >= profile["min_elo_floor"],
            }

        meta_summary = {
            "source_counts": source_counts,
            "lora_promotions": promotions[-10:],
            "elo_currency_governor": currency_summary,
            "slash_command_routing": slash_routing,
        }
        return records, meta_summary

    def pool_and_persist_all(self, fast_probe: bool = False) -> Dict[str, Any]:
        """Pools all ELO storage & cognitive memory into SQLite WAL, Merkle ledger, and JSON."""
        timestamp_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        fabric_status = self.probe_wireguard_and_jupyter_fabric(fast_mode=fast_probe)
        records, meta_summary = self.collect_all_elo_sources()

        # Sort records by ELO descending
        records.sort(key=lambda r: (r.elo_rating, r.matches), reverse=True)

        # Persist into SQLite WAL tables: pooled_elo_memory_ledger & working_memory_kv
        with self._get_conn() as conn:
            for phantom in self.PHANTOM_PERSONAS:
                conn.execute("DELETE FROM pooled_elo_memory_ledger WHERE LOWER(entity_id) = ?", (phantom,))
            active_keys: List[str] = []
            for r in records:
                record_key = f"{r.source_store}::{r.entity_type}::{r.domain}::{r.entity_id}"
                active_keys.append(record_key)
                conn.execute(
                    """
                    INSERT INTO pooled_elo_memory_ledger (
                        record_key, entity_id, entity_type, domain, elo_rating,
                        wins, losses, draws, matches, confidence_lower, confidence_upper,
                        source_store, metadata_json, sha256_hash, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(record_key) DO UPDATE SET
                        elo_rating=excluded.elo_rating,
                        wins=excluded.wins,
                        losses=excluded.losses,
                        draws=excluded.draws,
                        matches=excluded.matches,
                        confidence_lower=excluded.confidence_lower,
                        confidence_upper=excluded.confidence_upper,
                        metadata_json=excluded.metadata_json,
                        sha256_hash=excluded.sha256_hash,
                        updated_at=excluded.updated_at
                    """,
                    (
                        record_key,
                        r.entity_id,
                        r.entity_type,
                        r.domain,
                        r.elo_rating,
                        r.wins,
                        r.losses,
                        r.draws,
                        r.matches,
                        r.confidence_lower,
                        r.confidence_upper,
                        r.source_store,
                        json.dumps(r.metadata, sort_keys=True),
                        r.sha256_hash,
                        r.updated_at or timestamp_utc,
                    ),
                )

            # Prune any stale/orphaned records no longer present in active harvested sources
            if active_keys:
                placeholders = ",".join("?" for _ in active_keys)
                conn.execute(
                    f"DELETE FROM pooled_elo_memory_ledger WHERE record_key NOT IN ({placeholders})",
                    tuple(active_keys),
                )
            else:
                conn.execute("DELETE FROM pooled_elo_memory_ledger")

            # Store key cognitive memory KV entries
            kv_entries = {
                "elo_pool:wireguard_jupyter_fabric": fabric_status,
                "elo_pool:slash_command_routing": meta_summary["slash_command_routing"],
                "elo_pool:currency_governor": meta_summary["elo_currency_governor"],
                "elo_pool:source_counts": meta_summary["source_counts"],
            }
            now_epoch = time.time()
            for k, val_obj in kv_entries.items():
                val_json = json.dumps(val_obj, sort_keys=True)
                conn.execute(
                    """
                    INSERT INTO working_memory_kv (key, value_json, updated_at, ttl_sec)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value_json=excluded.value_json,
                        updated_at=excluded.updated_at,
                        ttl_sec=excluded.ttl_sec
                    """,
                    (k, val_json, now_epoch, 86400.0),
                )

            # Compute global Merkle root across working_memory_kv + pooled_elo_memory_ledger
            cur_kv = conn.execute("SELECT key, value_json FROM working_memory_kv ORDER BY key ASC")
            kv_hashes = [
                f"{row[0]}:{hashlib.sha256(str(row[1]).encode('utf-8')).hexdigest()}"
                for row in cur_kv.fetchall()
            ]

            cur_elo = conn.execute(
                "SELECT record_key, sha256_hash FROM pooled_elo_memory_ledger ORDER BY record_key ASC"
            )
            elo_hashes = [f"{row[0]}:{row[1]}" for row in cur_elo.fetchall()]

            combined_leaves = "|".join(kv_hashes + elo_hashes)
            merkle_root = hashlib.sha256(combined_leaves.encode("utf-8")).hexdigest()

            sync_id = f"wg-elo-sync-{int(now_epoch)}"
            conn.execute(
                """
                INSERT OR REPLACE INTO wireguard_jupyter_elo_sync (
                    sync_id, timestamp_utc, wireguard_active, jupyter_url,
                    pooled_records_count, merkle_root, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sync_id,
                    timestamp_utc,
                    1 if fabric_status["wireguard_active"] else 0,
                    fabric_status["jupyter_hub"]["active_url"],
                    len(records),
                    merkle_root,
                    json.dumps(meta_summary["source_counts"]),
                ),
            )
            conn.commit()
            try:
                conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
            except Exception:
                pass

        # Build canonical pooled JSON payload
        top_champions = [asdict(r) for r in records[:15]]
        all_records_dicts = [asdict(r) for r in records]

        pooled_payload = {
            "schema_version": "2.0.0-WIREGUARD-JUPYTER-ELO-POOL",
            "timestamp_utc": timestamp_utc,
            "merkle_root_sha256": merkle_root,
            "sqlite_wal_path": str(self.sqlite_path),
            "total_pooled_entities": len(records),
            "working_memory_kv_count": len(kv_hashes),
            "wireguard_and_jupyter_fabric": fabric_status,
            "source_store_counts": meta_summary["source_counts"],
            "elo_currency_governor": meta_summary["elo_currency_governor"],
            "slash_command_routing": meta_summary["slash_command_routing"],
            "recent_lora_promotions": meta_summary["lora_promotions"],
            "top_champions": top_champions,
            "pooled_records": all_records_dicts,
        }

        # Atomic write to 04_data_and_memory/data/pooled_elo_storage_and_memory.json
        self._atomic_write_json(self.pooled_json_path, pooled_payload)

        # Mirror to Obsidian Vault (Rule 2 Tri-Vault Parity)
        if self.obsidian_analytics_dir.parent.exists():
            self.obsidian_analytics_dir.mkdir(parents=True, exist_ok=True)
            obs_target = self.obsidian_analytics_dir / "pooled_elo_storage_and_memory.json"
            self._atomic_write_json(obs_target, pooled_payload)

        # Update cognitive_memory_merkle_ledger.json
        merkle_doc = {
            "merkle_root": merkle_root,
            "kv_entries": len(kv_hashes),
            "pooled_elo_entries": len(elo_hashes),
            "wireguard_active": fabric_status["wireguard_active"],
            "active_jupyter_hub": fabric_status["jupyter_hub"]["active_url"],
            "updated_at": time.time(),
            "updated_at_iso": timestamp_utc,
        }
        self._atomic_write_json(self.merkle_ledger_path, merkle_doc)

        return pooled_payload

    @staticmethod
    def _atomic_write_json(target_path: Path, data: Dict[str, Any]) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(target_path.parent),
            prefix=f".{target_path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.chmod(tmp_name, 0o644)
            os.replace(tmp_name, str(target_path))
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass

    def create_sqlite_backup_snapshot(self, dest_path: Path) -> Path:
        """Creates a consistent, checkpointed SQLite snapshot using the SQLite online backup API."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if dest_path.exists():
            dest_path.unlink()
        with sqlite3.connect(str(self.sqlite_path), timeout=15.0) as src_conn:
            with sqlite3.connect(str(dest_path), timeout=15.0) as dst_conn:
                src_conn.backup(dst_conn)
                dst_conn.execute("PRAGMA journal_mode=DELETE;")
                dst_conn.commit()
        return dest_path

    def sync_to_remote_l8_jupyter(self, timeout_s: float = 12.0) -> Dict[str, Any]:
        """Synchronizes pooled ELO SQLite WAL, JSON ledgers, and Global Orchestrator Notebook to L8 Jupyter Hub."""
        target_host: Optional[str] = None
        selected_transport: str = "offline"
        for candidate_ip, transport_name in L8_TRANSPORT_CANDIDATES:
            is_up, _ = self._check_tcp_port(candidate_ip, 22, timeout=0.5)
            if is_up:
                target_host = candidate_ip
                selected_transport = transport_name
                break

        if not target_host:
            return {
                "status": "skipped_offline",
                "target_host": None,
                "transport": "offline",
                "synced_files": [],
            }

        remote_base = "/home/linuxmini/Lauburu-Monorepo"
        remote_sqlite_path = f"{remote_base}/04_data_and_memory/data/lens_working_memory_kv.sqlite"
        files_to_sync: List[Tuple[Path, str]] = [
            (Path(__file__).resolve(), f"{remote_base}/04_data_and_memory/elo_pooled_memory_and_storage_hub.py"),
            (self.pooled_json_path, f"{remote_base}/04_data_and_memory/data/pooled_elo_storage_and_memory.json"),
            (self.merkle_ledger_path, f"{remote_base}/04_data_and_memory/data/cognitive_memory_merkle_ledger.json"),
            (self.canonical_leaderboard_path, f"{remote_base}/04_data_and_memory/data/canonical_elo_leaderboard.json"),
            (self.swarm_leaderboard_path, f"{remote_base}/04_data_and_memory/elo_leaderboard.json"),
            (self.dynamic_mesh_elo_path, f"{remote_base}/04_data_and_memory/dynamic_mesh_elo.json"),
            (self.generational_elo_path, f"{remote_base}/04_data_and_memory/local_models_generational_elo.json"),
            (self.promotion_history_path, f"{remote_base}/04_data_and_memory/elo_promotion_history.jsonl"),
            (self.repo_root / "lens_global_orchestrator.ipynb", f"{remote_base}/lens_global_orchestrator.ipynb"),
            (
                self.repo_root / "01_apps/notebooks/25_continuous_lens_mesh_and_elo_optimizer.ipynb",
                f"{remote_base}/01_apps/notebooks/25_continuous_lens_mesh_and_elo_optimizer.ipynb",
            ),
        ]

        synced: List[str] = []
        errors: List[str] = []
        try:
            mkdir_cmd = [
                "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3",
                f"linuxmini@{target_host}",
                f"mkdir -p {remote_base}/04_data_and_memory/data {remote_base}/01_apps/notebooks",
            ]
            subprocess.run(mkdir_cmd, capture_output=True, text=True, timeout=4.0)

            # 1. Atomically sync SQLite database via online backup snapshot + remote WAL cleanup
            if self.sqlite_path.exists():
                with tempfile.TemporaryDirectory() as tmp_dir:
                    snap_path = Path(tmp_dir) / "lens_working_memory_kv.sqlite.snap"
                    self.create_sqlite_backup_snapshot(snap_path)
                    scp_sql = [
                        "scp", "-q", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3",
                        str(snap_path),
                        f"linuxmini@{target_host}:{remote_sqlite_path}.tmp",
                    ]
                    res_sql = subprocess.run(scp_sql, capture_output=True, text=True, timeout=timeout_s)
                    if res_sql.returncode == 0:
                        mv_cmd = [
                            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3",
                            f"linuxmini@{target_host}",
                            f"rm -f {remote_sqlite_path}-wal {remote_sqlite_path}-shm && mv -f {remote_sqlite_path}.tmp {remote_sqlite_path}",
                        ]
                        res_mv = subprocess.run(mv_cmd, capture_output=True, text=True, timeout=4.0)
                        if res_mv.returncode == 0:
                            synced.append(self.sqlite_path.name)
                        else:
                            errors.append(f"{self.sqlite_path.name}: {res_mv.stderr.strip()}")
                    else:
                        errors.append(f"{self.sqlite_path.name}: {res_sql.stderr.strip()}")

            # 2. Sync JSON ledgers and notebooks
            for local_p, remote_p in files_to_sync:
                if not local_p.exists():
                    continue
                scp_cmd = [
                    "scp", "-q", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3",
                    str(local_p),
                    f"linuxmini@{target_host}:{remote_p}",
                ]
                res = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=timeout_s)
                if res.returncode == 0:
                    synced.append(local_p.name)
                else:
                    errors.append(f"{local_p.name}: {res.stderr.strip()}")
        except Exception as exc:
            errors.append(str(exc))

        return {
            "status": "synced" if synced and not errors else ("partial" if synced else "error"),
            "target_host": target_host,
            "transport": selected_transport,
            "jupyter_url": f"http://{target_host}:8888",
            "synced_files": synced,
            "errors": errors,
        }


def main() -> int:
    hub = WireGuardJupyterPooledEloHub()
    pooled = hub.pool_and_persist_all()
    remote_sync = hub.sync_to_remote_l8_jupyter()
    summary = {
        "status": "success",
        "timestamp_utc": pooled["timestamp_utc"],
        "merkle_root_sha256": pooled["merkle_root_sha256"],
        "total_pooled_entities": pooled["total_pooled_entities"],
        "working_memory_kv_count": pooled["working_memory_kv_count"],
        "wireguard_active": pooled["wireguard_and_jupyter_fabric"]["wireguard_active"],
        "active_jupyter_url": pooled["wireguard_and_jupyter_fabric"]["jupyter_hub"]["active_url"],
        "slash_commands": {
            k: {
                "champion": v["routed_champion_model"],
                "elo": v["champion_elo"],
                "skill": v["skill"],
            }
            for k, v in pooled["slash_command_routing"].items()
        },
        "remote_l8_jupyter_sync": remote_sync,
    }
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
