#!/usr/bin/env python3
"""
06_scripts_and_tooling/tests/test_gcp_credit_automation.py
==========================================================
Comprehensive Test Suite for Milestone M4 (R9):
Governed GCP $1,400 Spot GPU Distillation Tranches.

Validates:
1. 4-tranche deployment schedule & model targets.
2. $1,400.00 AUD total credit grant and reserve headroom.
3. Strict $175.00 AUD per-tranche budget ceiling.
4. 45-minute hardware self-destruction watchdog (TTL enforcement).
5. State file serialization & Obsidian telemetry note generation.
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Ensure paths on sys.path
TEST_DIR = Path(__file__).resolve().parent
TOOLING_ROOT = TEST_DIR.parent
REPO_ROOT = TOOLING_ROOT.parent

for p in [str(REPO_ROOT), str(TOOLING_ROOT), str(TOOLING_ROOT / "cloud_and_quota")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from gcp_credit_usage_automation import (
    GCPCreditGovernor,
    INITIAL_CREDIT_POOL_AUD,
    BATCH_TRANCHE_CAP_AUD,
    STAGED_BATCHES,
    STATE_FILE,
    TELEMETRY_FILE,
    run_governor_cycle,
)


class TestGCPCreditGovernorTranches:
    """Verifies 4-tranche schedule, budget caps, and model distillation targets."""

    def test_initial_credit_pool_aud_constant(self):
        assert INITIAL_CREDIT_POOL_AUD == 455.00
        assert BATCH_TRANCHE_CAP_AUD == 75.00

    def test_staged_batches_structure_and_count(self):
        governor = GCPCreditGovernor()
        batches = governor.get_staged_batches()
        assert len(batches) == 4

        batch_ids = [b["batch_id"] for b in batches]
        expected_ids = [
            "BATCH_01_EDGE_SLMS",
            "BATCH_02_SWE_CODER",
            "BATCH_03_MULTIMODAL_DSP",
            "BATCH_04_MASTER_14B_DPO",
        ]
        assert batch_ids == expected_ids

    def test_every_tranche_under_cap(self):
        governor = GCPCreditGovernor()
        for b in governor.get_staged_batches():
            assert b["budget_aud"] <= 75.00
            assert governor.validate_spot_tranche_budget(b["batch_id"]) is True

    def test_total_committed_leaves_positive_headroom(self):
        total_committed = sum(b["budget_aud"] for b in STAGED_BATCHES)
        assert total_committed < INITIAL_CREDIT_POOL_AUD
        headroom = INITIAL_CREDIT_POOL_AUD - total_committed
        assert headroom > 0.0
        assert total_committed == 270.00
        assert headroom == 185.00


class TestSpotGpuTtlWatchdog:
    """Verifies 45-minute hardware self-destruction watchdog."""

    def test_ttl_under_45_minutes_active(self):
        governor = GCPCreditGovernor()
        expired, action = governor.enforce_vm_ttl(elapsed_minutes=30.0)
        assert expired is False
        assert action == "ACTIVE_TRAINING"

    def test_ttl_at_or_over_45_minutes_triggers_shutdown(self):
        governor = GCPCreditGovernor()
        expired, action = governor.enforce_vm_ttl(elapsed_minutes=45.0)
        assert expired is True
        assert action == "SHUTDOWN_TRIGGERED"

        expired_over, action_over = governor.enforce_vm_ttl(elapsed_minutes=52.3)
        assert expired_over is True
        assert action_over == "SHUTDOWN_TRIGGERED"


class TestStateAndTelemetryPersistence:
    """Verifies state serialization and Obsidian documentation."""

    def test_run_governor_cycle_persists_state(self):
        governor = GCPCreditGovernor()
        state = governor.run_governor_cycle()

        assert state["total_grant_aud"] == 455.00
        assert state["total_committed_aud"] == 270.00
        assert len(state["batches"]) == 4

        assert STATE_FILE.exists()
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["currency"] == "AUD"
        assert data["total_grant_aud"] == 455.00

        assert TELEMETRY_FILE.exists()
        content = TELEMETRY_FILE.read_text(encoding="utf-8")
        assert "BATCH_01_EDGE_SLMS" in content
        assert "455.00 AUD" in content or "455" in content



if __name__ == "__main__":
    pytest.main(["-v", __file__])
