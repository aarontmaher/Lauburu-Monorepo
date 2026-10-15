#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Comprehensive Test Suite: Tri-Vault Distillation, ELO Math & Leaderboard API
================================================================================
Subsystem: 05_agents_and_swarms/test_tri_vault_elo.py
Milestone: M4 — Continuous Tri-Vault Distillation & Real-Time ELO Leaderboard
Lauburu Mesh Ecosystem — 2026

Test Categories:
1. Bradley-Terry Logistic ELO Math Invariants (Expected score, symmetry, margin multiplier, zero-sum conservation).
2. Atomic JSON Persistence & Concurrency Safety (POSIX atomic rename, fsync, zero corruption).
3. Tri-Vault Obsidian Synchronization (YAML frontmatter, Wikilinks, ELO sorting, medal badges).
4. Continuous LoRA Dataset Serialization (Valid JSONL, mandatory schema keys, zero-mock, dual-sink mirror).
5. Port 8088 Dynamic Leaderboard API Verification (FastAPI TestClient, live dynamic reload without reboot).
6. 6-Swarm Tournament Engine (Round-robin 15 pairings, challenger mode, match recording).
================================================================================
"""

import os
import sys
import json
import time
import math
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any, List
import pytest

# Ensure monorepo modules in sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_PORTAL_DIR = REPO_ROOT / "01_apps" / "web_tui_portal"
SWARMS_DIR = REPO_ROOT / "05_agents_and_swarms"
DATA_DIR = REPO_ROOT / "04_data_and_memory"
OBSIDIAN_DIR = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS"

for p in [str(REPO_ROOT), str(WEB_PORTAL_DIR), str(SWARMS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient
from serve_portal import app
from leaderboard_dashboard import (
    load_dynamic_swarms,
    SWARM_LEADERBOARD_FILE,
    OPTIMAL_SWARMS
)
from swarm_tournament_and_continuous_trainer import (
    INITIAL_SWARMS,
    CANONICAL_SWARMS_CATALOG,
    calculate_expected_elo,
    compute_expected_pair,
    compute_dynamic_k,
    update_swarm_ratings,
    validate_lora_trajectory_schema,
    atomic_save_json,
    append_lora_trajectory_dual_sink,
    generate_obsidian_dashboard,
    SwarmELOTournamentEngine,
    SwarmMatchResult,
    LEADERBOARD_FILE,
    DASHBOARD_FILE,
    MASTER_LORA,
    DFS_LORA_FILE,
    run_swarm_training_cycle
)


# ==============================================================================
# 1. Bradley-Terry Logistic ELO Mathematical Invariants
# ==============================================================================

class TestBradleyTerryEloMath:
    """Verifies logistic probability distribution, expected scores, and update bounds."""

    def test_expected_score_symmetry_and_sum(self):
        """E_A + E_B must strictly equal 1.0 for arbitrary rating pairs."""
        pairs = [(2000.0, 2000.0), (2400.0, 1900.0), (1500.0, 2500.0), (1800.0, 1800.0), (2185.0, 1960.0)]
        for r_a, r_b in pairs:
            e_a, e_b = compute_expected_pair(r_a, r_b)
            assert math.isclose(e_a + e_b, 1.0, rel_tol=1e-9), f"Expectation sum failed for ({r_a}, {r_b})"

    def test_equal_ratings_yield_50_percent_win_prob(self):
        """Two identically rated swarms have exactly 0.50 expected score."""
        e_a = calculate_expected_elo(2100.0, 2100.0)
        assert math.isclose(e_a, 0.50, abs_tol=1e-6)

    def test_400_point_delta_yield_approx_91_percent(self):
        """A +400 rating advantage corresponds to ~90.91% expected win probability."""
        e_a = calculate_expected_elo(2400.0, 2000.0)
        expected = 10.0 / 11.0  # 0.9090909...
        assert math.isclose(e_a, expected, rel_tol=1e-5)

    def test_rating_conservation_in_head_to_head(self):
        """Zero-sum property: delta_a + delta_b must equal 0.0."""
        r_a_init, r_b_init = 2200.0, 1950.0
        _, _, delta_a, delta_b = update_swarm_ratings(r_a_init, r_b_init, score_a=1.0, k_factor=32.0)
        assert delta_a + delta_b == 0.0, f"Deltas {delta_a} + {delta_b} must sum to 0.0"

    def test_underdog_upset_yields_larger_gain_than_favorite_win(self):
        """Underdog winning yields much higher rating delta than favorite winning."""
        fav, dog = 2300.0, 1900.0
        _, _, fav_delta, _ = update_swarm_ratings(fav, dog, score_a=1.0, k_factor=32.0)
        _, _, dog_delta, _ = update_swarm_ratings(dog, fav, score_a=1.0, k_factor=32.0)

        assert dog_delta > fav_delta * 4.0, f"Dog gain {dog_delta} should dwarf fav gain {fav_delta}"

    def test_dynamic_k_factor_bounds_and_margin_scaling(self):
        """Verifies K_dyn in [8.0, 96.0] and monotonic scaling with MCTS margin."""
        k_close = compute_dynamic_k(matches_played_a=50, matches_played_b=50, mcts_margin=0.01)
        k_blowout = compute_dynamic_k(matches_played_a=50, matches_played_b=50, mcts_margin=0.80)

        assert 8.0 <= k_close <= 96.0
        assert 8.0 <= k_blowout <= 96.0
        assert k_blowout > k_close, "Blowout margin must produce higher K-factor"

    def test_rule_zero_unverified_yields_zero_k_factor(self):
        """When truth_verified is False, compute_dynamic_k clamps to lower bound."""
        k_unverified = compute_dynamic_k(truth_verified=False)
        assert k_unverified == 8.0  # Lower bound clamp


# ==============================================================================
# 2. Atomic JSON Persistence & Concurrency Safety
# ==============================================================================

class TestAtomicJsonPersistence:
    """Verifies POSIX atomic replacement, absence of partial writes, and schema compliance."""

    def test_atomic_save_json_creates_valid_file(self, tmp_path):
        target = tmp_path / "test_leaderboard.json"
        data = {"timestamp": "2026-08-31T00:00:00Z", "total_swarms": 6, "swarms": INITIAL_SWARMS}
        success = atomic_save_json(target, data)
        assert success is True
        assert target.exists()

        with open(target, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["total_swarms"] == 6
        assert len(loaded["swarms"]) == 6

    def test_concurrent_writers_and_readers_resilience(self, tmp_path):
        """High-frequency parallel writes and reads must never produce JSONDecodeError."""
        target = tmp_path / "concurrent_swarm_leaderboard.json"
        errors = []
        stop_event = threading.Event()

        def writer_loop():
            step = 0
            while not stop_event.is_set():
                step += 1
                payload = {
                    "timestamp": time.time(),
                    "step": step,
                    "champion": f"Champion_{step % 6}",
                    "swarms": [{"id": i, "elo": 2000.0 + step + i} for i in range(6)]
                }
                try:
                    atomic_save_json(target, payload)
                except Exception as e:
                    errors.append(f"Writer error: {e}")
                time.sleep(0.001)

        def reader_loop():
            while not stop_event.is_set():
                if target.exists():
                    try:
                        with open(target, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        assert "step" in data
                    except Exception as e:
                        errors.append(f"Reader error (partial read): {e}")
                time.sleep(0.001)

        w_thread = threading.Thread(target=writer_loop)
        r_threads = [threading.Thread(target=reader_loop) for _ in range(4)]

        w_thread.start()
        for r in r_threads:
            r.start()

        time.sleep(0.4)
        stop_event.set()

        w_thread.join()
        for r in r_threads:
            r.join()

        assert len(errors) == 0, f"Encountered concurrency errors: {errors}"

    def test_swarm_elo_leaderboard_canonical_schema(self):
        """Validates canonical swarm_elo_leaderboard.json against required production schema."""
        assert SWARM_LEADERBOARD_FILE.exists()
        with open(SWARM_LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "champion_swarm" in data
        assert "swarms" in data
        assert len(data["swarms"]) == 6

        mandatory_fields = [
            "swarm_id", "name", "tagline", "elo", "synergy_pct",
            "mcts_pass_rate", "vram_gb", "cloud_spend", "lead_model", "critic_model"
        ]
        for s in data["swarms"]:
            for field in mandatory_fields:
                assert field in s, f"Swarm {s.get('name')} missing mandatory field: {field}"
            assert isinstance(s["elo"], (int, float))
            assert s["elo"] > 1000.0


# ==============================================================================
# 3. Tri-Vault Obsidian Synchronization
# ==============================================================================

class TestTriVaultObsidianSync:
    """Verifies SWARM_ELO_LEADERBOARD_AND_TRAINING_2026.md formatting, Wikilinks, and badges."""

    def test_obsidian_dashboard_generation_content_and_wikilinks(self, tmp_path):
        target_md = tmp_path / "SWARM_ELO_LEADERBOARD_AND_TRAINING_2026.md"
        swarms = [dict(s) for s in INITIAL_SWARMS]
        swarms[0]["elo"] = 2450.0  # Champion

        success = generate_obsidian_dashboard(swarms, target_md)
        assert success is True
        assert target_md.exists()

        content = target_md.read_text(encoding="utf-8")
        assert "tags: [swarm, elo, leaderboard" in content
        assert "champion_swarm:" in content
        assert "total_swarms: 6" in content
        assert "zero_mock_certified: true" in content
        assert "🥇" in content
        assert "🥈" in content
        assert "🥉" in content
        assert "## 1. 🏆 Canonical Swarm ELO Rankings" in content
        assert "## 2. 🧠 Champion Swarm Deep Dive:" in content
        assert "## 3. 🛡️ Continuous Swarm Training & Distillation Rules" in content
        assert "## 4. 🔗 Tri-Vault Canonical Knowledge Graph" in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in content
        assert "[[Index]]" in content

    def test_live_obsidian_dashboard_file_integrity(self):
        """Verifies active repository dashboard note satisfies all invariants."""
        if not DASHBOARD_FILE.exists():
            generate_obsidian_dashboard(INITIAL_SWARMS, DASHBOARD_FILE)

        assert DASHBOARD_FILE.exists()
        content = DASHBOARD_FILE.read_text(encoding="utf-8")
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in content
        assert "[[Index]]" in content


# ==============================================================================
# 4. Continuous LoRA Dataset Serialization & Schema Validation
# ==============================================================================

class TestContinuousLoRAIngestion:
    """Verifies continuous_lora_dataset.jsonl schema, formatting, and zero-mock integrity."""

    def test_valid_trajectory_schema(self):
        sample = {
            "instruction": "Solve benchmark task django__django-11099 via multi-agent consensus.",
            "thought": "1. [AgentWorld]: Verified AST syntax. 2. [WebWorld]: Verified DOM.",
            "output": "Verified Solution diff for django__django-11099.",
            "swarm": "👑 Dual-World Sovereign Mesh Swarm",
            "category": "swe_bench_training_round",
            "instance_id": "django__django-11099",
            "cloud_spend_aud": 0.00,
            "truth_verified": True,
            "zero_mock": True,
            "truth_compliance_pct": 100.0
        }
        valid, msg = validate_lora_trajectory_schema(sample)
        assert valid is True, msg

    def test_schema_validator_rejects_missing_keys(self):
        sample = {
            "instruction": "Test",
            "thought": "Test",
            # missing output, swarm, etc.
        }
        valid, msg = validate_lora_trajectory_schema(sample)
        assert valid is False
        assert "Missing" in msg

    def test_schema_validator_rejects_non_zero_cloud_spend(self):
        sample = {
            "instruction": "Test instruction",
            "thought": "Test thought",
            "output": "Test output",
            "swarm": "👑 Dual-World Sovereign Mesh Swarm",
            "category": "swe_bench",
            "instance_id": "test-123",
            "cloud_spend_aud": 0.50,  # Violation
            "truth_verified": True,
            "zero_mock": True,
            "truth_compliance_pct": 100.0
        }
        valid, msg = validate_lora_trajectory_schema(sample)
        assert valid is False
        assert "Spend Violation" in msg

    def test_schema_validator_rejects_mock_data(self):
        sample = {
            "instruction": "Test instruction with mock_dummy keyword",
            "thought": "Test thought",
            "output": "Test output",
            "swarm": "👑 Dual-World Sovereign Mesh Swarm",
            "category": "swe_bench",
            "instance_id": "test-123",
            "cloud_spend_aud": 0.00,
            "truth_verified": True,
            "zero_mock": True,
            "truth_compliance_pct": 100.0
        }
        valid, msg = validate_lora_trajectory_schema(sample)
        assert valid is False
        assert "mock" in msg.lower()

    def test_dual_sink_mirror_append(self, tmp_path):
        prim = tmp_path / "primary_continuous.jsonl"
        sec = tmp_path / "secondary_continuous.jsonl"

        sample = {
            "instruction": "Solve test-dual-sink instance",
            "thought": "Dual sink test thought chain",
            "output": "Verified dual sink output",
            "swarm": "👑 Dual-World Sovereign Mesh Swarm",
            "category": "swe_bench_training_round",
            "instance_id": "test-dual-sink-001",
            "cloud_spend_aud": 0.00,
            "truth_verified": True,
            "zero_mock": True,
            "truth_compliance_pct": 100.0
        }

        success = append_lora_trajectory_dual_sink(sample, prim, sec)
        assert success is True
        assert prim.exists()
        assert sec.exists()

        p_line = json.loads(prim.read_text(encoding="utf-8").strip())
        s_line = json.loads(sec.read_text(encoding="utf-8").strip())
        assert p_line["instance_id"] == "test-dual-sink-001"
        assert s_line["instance_id"] == "test-dual-sink-001"
        assert p_line["cloud_spend_aud"] == 0.00


# ==============================================================================
# 5. Port 8088 Dynamic Leaderboard API Verification
# ==============================================================================

class TestPort8088DynamicLeaderboardApi:
    """Verifies live FastAPI endpoints on Port 8088 and dynamic disk reload without reboot."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_api_status_endpoint(self, client):
        """GET /api/status returns HTTP 200 with HEALTHY status and Port 8088."""
        res = client.get("/api/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert data["port"] == 8088
        assert data["fps"] == 120
        assert data["total_apps"] >= 8

    def test_api_leaderboard_data_schema(self, client):
        """GET /api/leaderboard/data returns all mandatory data structures."""
        res = client.get("/api/leaderboard/data")
        assert res.status_code == 200
        data = res.json()

        assert "models" in data
        assert "counts" in data
        assert "swarms" in data
        assert "transports" in data
        assert "categories" in data
        assert "training" in data
        assert "timestamp" in data

        assert data["counts"]["all"] >= 20
        assert len(data["transports"]) >= 5
        assert len(data["categories"]) == 7
        assert len(data["swarms"]) >= 5

    def test_api_leaderboard_dynamic_reload_without_server_restart(self, client, monkeypatch, tmp_path):
        """Mutating the JSON leaderboard on disk is immediately reflected in the API response."""
        mock_file = tmp_path / "mock_swarm_elo_leaderboard.json"
        
        # 1. Write Initial State (Dual-World at 2200.0)
        initial_data = {
            "timestamp": "2026-08-31T00:00:00Z",
            "champion_swarm": "👑 Dual-World Sovereign Mesh Swarm",
            "total_swarms": 6,
            "swarms": [
                {
                    "swarm_id": "SWARM_DUAL_WORLD_SOVEREIGN",
                    "name": "👑 Dual-World Sovereign Mesh Swarm",
                    "elo": 2200.0,
                    "synergy_pct": 99.0,
                    "mcts_pass_rate": "36/36 (100%)",
                    "vram_gb": 50.9,
                    "battles_won": 100,
                    "battles_total": 100
                }
            ]
        }
        atomic_save_json(mock_file, initial_data)

        # Monkeypatch leaderboard file path
        import leaderboard_dashboard
        monkeypatch.setattr(leaderboard_dashboard, "SWARM_LEADERBOARD_FILE", mock_file)

        res1 = client.get("/api/leaderboard/data")
        assert res1.status_code == 200
        swarms1 = res1.json()["swarms"]
        assert swarms1["dual_world"]["combined_elo"] == 2200.0

        # 2. Simulate Overnight Daemon Training Step (Dual-World rises to 2488.5)
        updated_data = dict(initial_data)
        updated_data["swarms"] = [dict(initial_data["swarms"][0])]
        updated_data["swarms"][0]["elo"] = 2488.5
        updated_data["swarms"][0]["battles_won"] = 150
        atomic_save_json(mock_file, updated_data)

        # 3. Subsequent Request Reflects Live Update Instantly
        res2 = client.get("/api/leaderboard/data")
        assert res2.status_code == 200
        swarms2 = res2.json()["swarms"]
        assert swarms2["dual_world"]["combined_elo"] == 2488.5
        assert swarms2["dual_world"]["battles_won"] == 150

    def test_leaderboard_html_page_rendering(self, client):
        """GET /leaderboard returns HTTP 200 with chart and table containers."""
        res = client.get("/leaderboard")
        assert res.status_code == 200
        html = res.text
        assert "Lauburu AI Leaderboard & Local AI Optimizer" in html
        assert 'id="radar-cvs"' in html
        assert 'id="lb-tbody"' in html
        assert 'id="refresh-ts"' in html
        assert "Chart.js" in html or "chart.umd.min.js" in html


# ==============================================================================
# 6. Tournament Engine Execution
# ==============================================================================

class TestTournamentEngine:
    """Verifies round-robin tournaments, challenger rounds, and ELO mutations."""

    def test_tournament_engine_initialization(self, tmp_path):
        lb_file = tmp_path / "test_swarms.json"
        md_file = tmp_path / "test_dash.md"
        lora_file = tmp_path / "test_lora.jsonl"
        sec_lora = tmp_path / "test_sec_lora.jsonl"

        engine = SwarmELOTournamentEngine(
            leaderboard_path=lb_file,
            obsidian_path=md_file,
            lora_path=lora_file,
            secondary_lora_path=sec_lora
        )
        assert len(engine.swarms) == 6
        assert lb_file.exists()

    def test_execute_match_zero_sum_and_persistence(self, tmp_path):
        lb_file = tmp_path / "test_swarms.json"
        md_file = tmp_path / "test_dash.md"
        lora_file = tmp_path / "test_lora.jsonl"
        sec_lora = tmp_path / "test_sec_lora.jsonl"

        engine = SwarmELOTournamentEngine(
            leaderboard_path=lb_file,
            obsidian_path=md_file,
            lora_path=lora_file,
            secondary_lora_path=sec_lora
        )

        task = {"instance_id": "test_task_1", "domain": "polyglot_code", "repo": "test/repo"}
        res = engine.execute_match(
            "SWARM_DUAL_WORLD_SOVEREIGN",
            "SWARM_GLOBAL_SOVEREIGN_FRONTIER",
            task=task,
            mcts_val_a=0.95,
            mcts_val_b=0.80
        )

        assert res.winner_id == "SWARM_DUAL_WORLD_SOVEREIGN"
        assert res.delta_elo_a + res.delta_elo_b == 0.0
        assert res.score_a == 1.0 and res.score_b == 0.0
        assert lora_file.exists()
        assert sec_lora.exists()
        assert md_file.exists()

    def test_round_robin_tournament_15_pairings(self, tmp_path):
        lb_file = tmp_path / "test_swarms.json"
        md_file = tmp_path / "test_dash.md"
        lora_file = tmp_path / "test_lora.jsonl"
        sec_lora = tmp_path / "test_sec_lora.jsonl"

        engine = SwarmELOTournamentEngine(
            leaderboard_path=lb_file,
            obsidian_path=md_file,
            lora_path=lora_file,
            secondary_lora_path=sec_lora
        )

        results = engine.run_full_round_robin_tournament()
        assert len(results) == 15, "6 swarms must produce exactly 15 pairwise matches"
        for r in results:
            assert r.delta_elo_a + r.delta_elo_b == 0.0

    def test_challenger_round_execution(self, tmp_path):
        lb_file = tmp_path / "test_swarms.json"
        md_file = tmp_path / "test_dash.md"
        lora_file = tmp_path / "test_lora.jsonl"
        sec_lora = tmp_path / "test_sec_lora.jsonl"

        engine = SwarmELOTournamentEngine(
            leaderboard_path=lb_file,
            obsidian_path=md_file,
            lora_path=lora_file,
            secondary_lora_path=sec_lora
        )

        res = engine.run_challenger_round()
        assert isinstance(res, SwarmMatchResult)
        assert res.delta_elo_a + res.delta_elo_b == 0.0


# ==============================================================================
# Main Test Execution Runner
# ==============================================================================

if __name__ == "__main__":
    pytest.main(["-v", __file__])
