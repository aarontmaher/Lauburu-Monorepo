#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04_data_and_memory/tests/test_elo_pooled_memory_and_storage_hub.py
==================================================================
Comprehensive Unit, Integration & Edge-Case Test Suite for the
WireGuard + Jupyter Notebook Pooled ELO Storage & Cognitive Memory Hub.

Verifies:
1. Multi-source ELO pooling across all 7 monorepo ELO stores into SQLite WAL & JSON
2. Cryptographic SHA-256 Merkle root calculation & cognitive_memory_merkle_ledger.json
3. Rule 15.7 Phantom Persona purging (zero fabricated/masked personas)
4. Slash-command dynamic ELO routing (/goal, /boost, /notebook-specialist, /teamwork-preview)
5. Edge cases: empty stores, corrupt JSON files, boundary Wilson confidence intervals (0/0, 100%, negative)
6. Global Orchestrator (:3037) /api/orchestrator/elo_pool GET/POST integration
7. Global Orchestrator & Companion Notebooks AST validity, Dual-Vault parity & WireGuard config
"""

from __future__ import annotations

import ast
import json
import socket
import sqlite3
import sys
import threading
import time
import urllib.request
from http.server import HTTPServer
from pathlib import Path
import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
if not REPO_ROOT.exists():
    REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DATA_MEM_DIR = REPO_ROOT / "04_data_and_memory"
LENS_SRC_DIR = REPO_ROOT / "01_apps" / "screen_lens" / "src"

for p in (str(DATA_MEM_DIR), str(LENS_SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from elo_pooled_memory_and_storage_hub import (
    L8_TRANSPORT_CANDIDATES,
    PooledEloRecord,
    WireGuardJupyterPooledEloHub,
    SLASH_COMMAND_PROFILES,
)


def test_wilson_interval_edge_cases():
    """Verify boundary values for Wilson confidence interval calculations."""
    # Zero total matches -> safe baseline [1400, 1600]
    low0, high0 = WireGuardJupyterPooledEloHub._wilson_interval(0, 0)
    assert low0 == 1400.0 and high0 == 1600.0

    # Negative total matches -> safe baseline
    low_neg, high_neg = WireGuardJupyterPooledEloHub._wilson_interval(5, -3)
    assert low_neg == 1400.0 and high_neg == 1600.0

    # 100% win rate
    low_win, high_win = WireGuardJupyterPooledEloHub._wilson_interval(50, 50)
    assert 1600.0 < low_win <= high_win <= 1800.0

    # 0% win rate
    low_loss, high_loss = WireGuardJupyterPooledEloHub._wilson_interval(0, 50)
    assert 1000.0 <= low_loss <= high_loss < 1200.0

    # Out-of-bounds wins > total clamped safely
    low_clamp, high_clamp = WireGuardJupyterPooledEloHub._wilson_interval(999, 10)
    assert low_clamp <= high_clamp <= 1800.0


def test_isolated_hub_empty_and_corrupt_inputs(tmp_path: Path):
    """Verify graceful handling when ELO JSON files are missing, empty, or corrupt."""
    data_dir = tmp_path / "04_data_and_memory"
    sub_dir = data_dir / "data"
    sub_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "obsidian_vault" / "04_ANALYTICS").mkdir(parents=True, exist_ok=True)

    # Write a corrupt JSON file to canonical_elo_leaderboard.json
    (sub_dir / "canonical_elo_leaderboard.json").write_text("{corrupt json", encoding="utf-8")
    # Write emptypromotion history
    (data_dir / "elo_promotion_history.jsonl").write_text("\n\n", encoding="utf-8")

    hub = WireGuardJupyterPooledEloHub(repo_root=tmp_path)
    res = hub.pool_and_persist_all(fast_probe=True)

    assert res["schema_version"] == "2.0.0-WIREGUARD-JUPYTER-ELO-POOL"
    assert len(res["merkle_root_sha256"]) == 64
    assert res["total_pooled_entities"] == 0
    assert (sub_dir / "pooled_elo_storage_and_memory.json").exists()
    assert (tmp_path / "obsidian_vault" / "04_ANALYTICS" / "pooled_elo_storage_and_memory.json").exists()


def test_phantom_persona_filtering_rule_15_7(tmp_path: Path):
    """Verify phantom personas (anthropic_fable_frontier, openai_astra_frontier, etc.) are purged."""
    data_dir = tmp_path / "04_data_and_memory"
    sub_dir = data_dir / "data"
    sub_dir.mkdir(parents=True, exist_ok=True)

    # Seed canonical leaderboard with 1 valid model and 2 phantom personas
    sample_lb = [
        {"model": "qwen2.5-0.5b-instruct-q4_k_m.gguf", "elo": 1372.7, "factual_accuracy_pct": 100.0},
        {"model": "anthropic_fable_frontier", "elo": 1999.9, "factual_accuracy_pct": 100.0},
        {"model": "Claude_Fable_5.1", "elo": 1999.9, "factual_accuracy_pct": 100.0},
    ]
    (sub_dir / "canonical_elo_leaderboard.json").write_text(json.dumps(sample_lb), encoding="utf-8")

    hub = WireGuardJupyterPooledEloHub(repo_root=tmp_path)
    # Also insert a phantom row into SQLite project_elo_leaderboard
    with hub._get_conn() as conn:
        conn.execute(
            """
            INSERT INTO project_elo_leaderboard (
                model_id, tier, task_domain, standard_benchmark_score,
                qwen_math_formal_score, internal_algorithm_score,
                calibrated_elo, hf_download_cmd, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("openai_astra_frontier", "FRONTIER_CLOUD", "coding_and_ast", 95.0, 95.0, 95.0, 1800.0, "none", time.time()),
        )
        conn.commit()

    pooled = hub.pool_and_persist_all(fast_probe=True)
    entity_ids = [r["entity_id"].lower() for r in pooled["pooled_records"]]
    assert "qwen2.5-0.5b-instruct-q4_k_m.gguf" in entity_ids
    assert "anthropic_fable_frontier" not in entity_ids
    assert "claude_fable_5.1" not in entity_ids
    assert "openai_astra_frontier" not in entity_ids


def test_stale_orphan_pruning_and_duplicate_deduplication(tmp_path: Path):
    """Verify duplicate source entries are deduplicated and stale SQLite ledger rows are pruned."""
    data_dir = tmp_path / "04_data_and_memory"
    sub_dir = data_dir / "data"
    sub_dir.mkdir(parents=True, exist_ok=True)

    # 1. Seed with duplicate entries for model_a and one entry for model_b
    sample_lb = [
        {"model": "model_a", "elo": 1300.0, "taxonomy": "Edge AI", "factual_accuracy_pct": 80.0},
        {"model": "model_a", "elo": 1450.0, "taxonomy": "Edge AI", "factual_accuracy_pct": 95.0},
        {"model": "model_b", "elo": 1250.0, "taxonomy": "Edge AI", "factual_accuracy_pct": 70.0},
    ]
    (sub_dir / "canonical_elo_leaderboard.json").write_text(json.dumps(sample_lb), encoding="utf-8")

    hub = WireGuardJupyterPooledEloHub(repo_root=tmp_path)
    pooled1 = hub.pool_and_persist_all(fast_probe=True)
    assert pooled1["total_pooled_entities"] == 2
    model_a_rec = [r for r in pooled1["pooled_records"] if r["entity_id"] == "model_a"][0]
    assert model_a_rec["elo_rating"] == 1450.0

    # 2. Remove model_b from JSON and verify re-pooling prunes model_b from SQLite ledger
    (sub_dir / "canonical_elo_leaderboard.json").write_text(
        json.dumps([{"model": "model_a", "elo": 1460.0, "taxonomy": "Edge AI"}]),
        encoding="utf-8",
    )
    pooled2 = hub.pool_and_persist_all(fast_probe=True)
    assert pooled2["total_pooled_entities"] == 1
    with sqlite3.connect(str(hub.sqlite_path)) as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM pooled_elo_memory_ledger").fetchone()[0]
        assert cnt == 1


def test_sqlite_online_backup_snapshot_with_concurrent_wal_reader(tmp_path: Path):
    """Verify create_sqlite_backup_snapshot produces a valid checkpointed DB while WAL reader is open."""
    sub_dir = tmp_path / "04_data_and_memory" / "data"
    sub_dir.mkdir(parents=True, exist_ok=True)
    (sub_dir / "canonical_elo_leaderboard.json").write_text(
        json.dumps([{"model": "qwen2.5-0.5b-instruct-q4_k_m.gguf", "elo": 1372.7}]),
        encoding="utf-8",
    )
    hub = WireGuardJupyterPooledEloHub(repo_root=tmp_path)
    # Hold a reader connection open so WAL cannot auto-checkpoint on writer close
    reader_conn = sqlite3.connect(str(hub.sqlite_path))
    reader_conn.execute("SELECT COUNT(*) FROM working_memory_kv").fetchall()
    try:
        hub.pool_and_persist_all(fast_probe=True)
        snap_file = tmp_path / "backup_snap.sqlite"
        hub.create_sqlite_backup_snapshot(snap_file)
        assert snap_file.exists()
        with sqlite3.connect(str(snap_file)) as snap_conn:
            integrity = snap_conn.execute("PRAGMA integrity_check;").fetchone()[0]
            assert integrity == "ok"
            cnt = snap_conn.execute("SELECT COUNT(*) FROM pooled_elo_memory_ledger").fetchone()[0]
            assert cnt == 1
    finally:
        reader_conn.close()


def test_l8_multi_transport_candidates_configured():
    """Verify L8 multi-transport fallback includes WireGuard, TB4, TB4 link-local, Tailscale, and LAN."""
    ips = [ip for ip, _ in L8_TRANSPORT_CANDIDATES]
    assert "10.1.0.17" in ips
    assert "10.0.0.8" in ips
    assert "169.254.65.244" in ips
    assert "100.121.247.8" in ips
    assert "192.168.8.242" in ips


def test_live_monorepo_elo_pooling_and_sqlite_wal():
    """Verify live monorepo ELO stores pool into SQLite WAL and JSON with valid Merkle root."""
    hub = WireGuardJupyterPooledEloHub(repo_root=REPO_ROOT)
    pooled = hub.pool_and_persist_all(fast_probe=True)

    assert pooled["total_pooled_entities"] >= 30
    assert len(pooled["merkle_root_sha256"]) == 64
    assert pooled["working_memory_kv_count"] >= 4

    # Verify all 4 required slash commands are routed
    routing = pooled["slash_command_routing"]
    for cmd in ("/goal", "/boost", "/notebook-specialist", "/teamwork-preview"):
        assert cmd in routing
        assert routing[cmd]["routed_champion_model"]
        assert routing[cmd]["champion_elo"] > 900.0
        assert routing[cmd]["elo_gate_passed"] is True

    # Verify SQLite WAL tables contain the pooled records
    with sqlite3.connect(str(hub.sqlite_path)) as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM pooled_elo_memory_ledger").fetchone()[0]
        assert cnt == pooled["total_pooled_entities"]
        sync_row = conn.execute(
            "SELECT merkle_root, jupyter_url FROM wireguard_jupyter_elo_sync ORDER BY sync_id DESC LIMIT 1"
        ).fetchone()
        assert sync_row is not None
        assert sync_row[0] == pooled["merkle_root_sha256"]
        assert ":8888" in sync_row[1]


def test_orchestrator_elo_pool_http_endpoints():
    """Verify Global Orchestrator HTTP server exposes GET and POST /api/orchestrator/elo_pool."""
    from lens_global_orchestrator import OrchestratorHTTPHandler

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    server = HTTPServer(("127.0.0.1", port), OrchestratorHTTPHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.05)

    base_url = f"http://127.0.0.1:{port}"
    try:
        # 1. GET /api/orchestrator/elo_pool
        with urllib.request.urlopen(f"{base_url}/api/orchestrator/elo_pool", timeout=5.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["schema_version"] == "2.0.0-WIREGUARD-JUPYTER-ELO-POOL"
            assert data["total_pooled_entities"] >= 30
            assert "/notebook-specialist" in data["slash_command_routing"]

        # 2. POST /api/orchestrator/elo_pool
        req = urllib.request.Request(
            f"{base_url}/api/orchestrator/elo_pool",
            data=json.dumps({"refresh": True, "sync_remote": False}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            assert resp.status == 200
            post_data = json.loads(resp.read().decode("utf-8"))
            assert len(post_data["merkle_root_sha256"]) == 64
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    "nb_rel",
    [
        "lens_global_orchestrator.ipynb",
        "01_apps/notebooks/lens_global_orchestrator.ipynb",
        "obsidian_vault/notebooks/lens_global_orchestrator.ipynb",
        "01_apps/notebooks/25_continuous_lens_mesh_and_elo_optimizer.ipynb",
        "obsidian_vault/notebooks/25_continuous_lens_mesh_and_elo_optimizer.ipynb",
    ],
)
def test_orchestrator_and_elo_notebooks_ast_and_wireguard_config(nb_rel: str):
    """Verify notebooks exist across Tri-Vault, parse cleanly via AST, and configure WireGuard + ELO pooling."""
    nb_path = REPO_ROOT / nb_rel
    assert nb_path.exists(), f"Missing notebook: {nb_path}"
    data = json.loads(nb_path.read_text(encoding="utf-8"))
    cells = data.get("cells", [])
    assert len(cells) >= 8

    full_source = ""
    for i, cell in enumerate(cells):
        src = "".join(cell.get("source", []))
        full_source += src + "\n"
        if cell.get("cell_type") == "code":
            assert src.strip() != "", f"Empty code cell {i} in {nb_rel}"
            ast.parse(src)

    assert "10.1.0.17:8888" in full_source
    assert "10.0.0.8:8888" in full_source
    assert "WireGuardJupyterPooledEloHub" in full_source

