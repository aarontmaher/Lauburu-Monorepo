#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Integration Tests: Telemetry Streamer & Rule 6.3 Storage Sentinel (R4 & R5)
Features 10, 11, 12, 13, 14:
- Feature 10: Live TUI Tab 5 Streaming (LoraTrainingJob, RAM governor, tournament table, NPU grants)
- Feature 11: Obsidian Analytics Sync with Derived Mathematical Proofs & Canonical Wikilinks
- Feature 12: Delta Lake / JSONL Logger (Training run receipts)
- Feature 13: Fast-Path Storage Invariant (< 3ms verification)
- Feature 14: Storage Self-Healing & Idempotent Cache Purger
"""

import os
import sys
import json
import time
import shutil
import pytest
from pathlib import Path

# Add paths
TEST_DIR = Path(__file__).resolve().parent
DATA_DIR = TEST_DIR.parent
if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))

from telemetry_streamer import TelemetryStreamer, StorageSentinel
from tri_vault_sink import TriVaultSink


@pytest.fixture
def test_env(tmp_path):
    obsidian_analytics = tmp_path / "obsidian_vault" / "04_ANALYTICS"
    obsidian_analytics.mkdir(parents=True, exist_ok=True)
    
    tui_config = tmp_path / "02_ai_models_and_inference" / "lauburu_tui" / "config"
    tui_config.mkdir(parents=True, exist_ok=True)

    data_dir = tmp_path / "04_data_and_memory"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "lora_datasets").mkdir(parents=True, exist_ok=True)

    sentinel = StorageSentinel(monorepo_root=tmp_path, min_free_gb=1.0)
    sink = TriVaultSink(lora_dir=data_dir / "lora_datasets", obsidian_dir=tmp_path / "obsidian_vault" / "01_DEBATES")
    streamer = TelemetryStreamer(monorepo_root=tmp_path, sentinel=sentinel, tri_vault_sink=sink)

    return {
        "root": tmp_path,
        "obsidian_analytics": obsidian_analytics,
        "tui_config": tui_config,
        "data_dir": data_dir,
        "sentinel": sentinel,
        "streamer": streamer,
        "sink": sink
    }


class TestFeature10LiveTUIStreaming:
    def test_stream_to_tui_creates_memory_fallback_json(self, test_env):
        streamer = test_env["streamer"]
        tui_config = test_env["tui_config"]

        ok = streamer.stream_to_tui(step=300, total_steps=5000, epoch=2, current_loss=1.45)
        assert ok is True

        fallback_file = tui_config / "memory_fallback.json"
        assert fallback_file.exists()

        with open(fallback_file, "r") as f:
            data = json.load(f)

        assert "lora_job" in data
        assert data["lora_job"]["current_step"] == 300
        assert data["lora_job"]["current_loss"] == 1.45
        assert data["lora_job"]["target_modules"] == "q_proj, v_proj, k_proj, o_proj"

        assert "ram_governor" in data
        assert "tier" in data["ram_governor"]
        assert "benchmark_rows" in data
        assert len(data["benchmark_rows"]) >= 3
        assert "npu_grants" in data
        assert len(data["npu_grants"]) >= 2

    def test_stream_to_tui_updates_optimization_strategies(self, test_env):
        streamer = test_env["streamer"]
        tui_config = test_env["tui_config"]

        streamer.stream_to_tui(step=100, current_loss=2.0)
        opt_file = tui_config / "optimization_strategies.json"
        assert opt_file.exists()

        with open(opt_file, "r") as f:
            data = json.load(f)
        assert "optimizations" in data
        assert len(data["optimizations"]) >= 3
        assert any("TB4 DMA" in opt["strategy"] for opt in data["optimizations"])

    def test_ram_governor_tier_computation(self, test_env):
        streamer = test_env["streamer"]
        assert streamer.compute_ram_governor_tier(90.0) == "Full"
        assert streamer.compute_ram_governor_tier(75.0) == "Medium"
        assert streamer.compute_ram_governor_tier(60.0) == "Minimal"
        assert streamer.compute_ram_governor_tier(40.0) == "EmergencyPause"


class TestFeature11ObsidianAnalyticsSync:
    def test_stream_to_obsidian_creates_markdown_note(self, test_env):
        streamer = test_env["streamer"]
        note = streamer.stream_to_obsidian(step=500, loss=1.25, lr=1e-4, headroom_gb=3.20)
        assert note.exists()

        content = note.read_text(encoding="utf-8")
        assert "---" in content  # Frontmatter
        assert "title: \"Qwen Math Continuous Optimization Trends" in content
        assert "Optimal TB4 Striping Weight:" in content
        assert "97.5%" in content
        assert "RAM Safety Status:" in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in content
        assert "[[Index]]" in content

    def test_stream_to_obsidian_closed_form_equations(self, test_env):
        streamer = test_env["streamer"]
        note = streamer.stream_to_obsidian(step=1000, loss=0.98, lr=5e-5, headroom_gb=3.20)
        content = note.read_text(encoding="utf-8")
        assert "Headroom = Cap (21.6GB)" in content
        assert "L(t) = 0.42 + 1.76 * exp(-0.0008 * t)" in content
        assert "w_i = (1 / RTT_i^2) / sum(1 / RTT_j^2)" in content


class TestFeature12DeltaLakeJsonlLogger:
    def test_log_training_run_appends_receipt(self, test_env):
        streamer = test_env["streamer"]
        data_dir = test_env["data_dir"]

        ram_gov = {"status": "CERTIFIED_HEALTHY", "headroom_gb": 3.2, "is_safe": True}
        ok = streamer.log_training_run(
            backend="mlx_metal",
            model="mlx-community/Qwen-AgentWorld-35B-A3B-4bit",
            iters=100,
            final_loss=2.0447,
            ram_governor=ram_gov,
            status="COMPLETED"
        )
        assert ok is True

        log_file = data_dir / "agentworld_training_runs.jsonl"
        assert log_file.exists()

        with open(log_file, "r") as f:
            lines = [json.loads(l) for l in f if l.strip()]

        assert len(lines) >= 1
        rec = lines[-1]
        assert rec["backend"] == "mlx_metal"
        assert rec["iters"] == 100
        assert rec["final_loss"] == 2.0447
        assert rec["status"] == "COMPLETED"


class TestFeature13FastPathStorageInvariant:
    def test_fast_path_latency_sub_3ms(self, test_env):
        sentinel = test_env["sentinel"]
        healthy, free_gb, dt_ms = sentinel.fast_path_check()
        assert dt_ms < 3.0, f"Latency {dt_ms}ms must be under 3.0ms (Rule 6.3 requirement)"
        assert free_gb >= 1.0
        assert healthy is True

    def test_fast_path_detects_unhealthy_on_missing_dir(self, tmp_path):
        bad_sentinel = StorageSentinel(monorepo_root=tmp_path / "nonexistent", min_free_gb=1000.0)
        healthy, free_gb, dt_ms = bad_sentinel.fast_path_check()
        assert healthy is False
        assert dt_ms < 3.0


class TestFeature14StorageSelfHealingPurger:
    def test_heal_storage_creates_missing_vault_directories(self, tmp_path):
        sentinel = StorageSentinel(monorepo_root=tmp_path, min_free_gb=1.0)
        assert not (tmp_path / "obsidian_vault").exists()

        res = sentinel.heal_storage_headroom()
        assert (tmp_path / "obsidian_vault").exists()
        assert (tmp_path / "04_data_and_memory").exists()
        assert res["rule_6_3_compliant"] is True

    def test_heal_storage_purges_transient_pycache(self, tmp_path):
        sentinel = StorageSentinel(monorepo_root=tmp_path, min_free_gb=1.0)
        pycache_dir = tmp_path / "sample_pkg" / "__pycache__"
        pycache_dir.mkdir(parents=True, exist_ok=True)
        (pycache_dir / "mod.cpython-313.pyc").write_text("sample bytecode")

        assert pycache_dir.exists()
        res = sentinel.heal_storage_headroom()
        assert not pycache_dir.exists()
        assert any("Purged __pycache__" in a for a in res["actions_taken"])

    def test_heal_storage_removes_stale_git_lock(self, tmp_path):
        sentinel = StorageSentinel(monorepo_root=tmp_path, min_free_gb=1.0)
        git_dir = tmp_path / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)
        lock_file = git_dir / "index.lock"
        lock_file.write_text("stale lock")

        # Set mtime to 15 seconds ago
        stale_time = time.time() - 15.0
        os.utime(lock_file, (stale_time, stale_time))

        assert lock_file.exists()
        res = sentinel.heal_storage_headroom()
        assert not lock_file.exists()
        assert any("Removed stale .git/index.lock" in a for a in res["actions_taken"])
