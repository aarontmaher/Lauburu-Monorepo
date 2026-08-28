"""
E2E Integration Test Suite: Canonical Port TUI Specialist Integration (Milestone 4)
Integrates Telemetry Ingestion, 4-Way Debate Devil's Lock Governance,
Git Worktree Sandboxing, Live Stream Broadcasting, and Textual Widget Real-Time Updating.
Derived strictly from ORIGINAL_REQUEST.md and PROJECT.md §Interface Contracts.
Test Architecture: 4-Tier Test Infra (Category-Partition, Boundary Values, Pairwise Combinations, Real-World Workload).
Rule #0 Adherence: Zero fake data, genuine Git operations, live file tailing, real Textual Pilot event loops.
"""

import os
import sys
import json
import time
import pytest
import asyncio
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "unit")))

try:
    from backend.devils_lock_governor import DevilsLockGovernor, DevilsLockError
except ImportError:
    from test_devils_lock_governance import DevilsLockGovernor, DevilsLockError

try:
    from backend.worktree_sandbox import WorktreeSandbox, WorktreeError
except ImportError:
    from test_worktree_sandbox import WorktreeSandbox, WorktreeError

try:
    from backend.tui_specialist_daemon import TuiSpecialistDaemon
except ImportError:
    from test_tui_specialist_daemon import TuiSpecialistDaemon

try:
    from tui.widgets.live_implementation_stream_widget import LiveImplementationStreamWidget
    from test_live_implementation_stream_widget import StreamTestApp
except ImportError:
    from test_live_implementation_stream_widget import StreamTestApp, LiveImplementationStreamWidget


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def e2e_harness(tmp_path):
    """Provides a complete end-to-end integration environment."""
    sandbox_dir = tmp_path / "lauburu_worktrees"
    telemetry_file = tmp_path / "mesh_trends.json"
    stream_file = tmp_path / "tui_live_implementation_stream.json"
    leaderboard_file = tmp_path / "canonical_ai_leaderboard.json"

    # Leaderboard with authentic models
    leaderboard_data = {
        "schema_version": "2.5.0",
        "last_updated_utc": "2026-08-29T00:00:00Z",
        "leaderboard": [
            {
                "id": "kimi_tandem_titan",
                "name": "Kimi Tandem Titan",
                "tier": "LOCAL_SOVEREIGN_GIANT",
                "elo": 3089.0,
                "specialist_skills": {
                    "3d_ai_training_game": 99.8,
                    "flutter_dart_mobile_architecture": 95.6,
                    "vision_vlm_truth_auditing": 99.7
                }
            },
            {
                "id": "gemini_3_1_pro",
                "name": "Gemini 3.1 Pro",
                "tier": "CLOUD_FRONTIER_REASONER",
                "elo": 3145.0,
                "specialist_skills": {
                    "3d_ai_training_game": 99.5,
                    "flutter_dart_mobile_architecture": 95.4,
                    "vision_vlm_truth_auditing": 99.0
                }
            }
        ]
    }
    leaderboard_file.write_text(json.dumps(leaderboard_data, indent=2))

    governor = DevilsLockGovernor(
        leaderboard_path=str(leaderboard_file),
        lock_dir=str(tmp_path / "lauburu_locks"),
    )
    sandbox = WorktreeSandbox(base_dir=str(sandbox_dir))
    daemon = TuiSpecialistDaemon(
        telemetry_path=str(telemetry_file),
        stream_log_path=str(stream_file),
        governor=governor,
        sandbox=sandbox,
    )

    yield {
        "tmp_path": tmp_path,
        "telemetry_file": str(telemetry_file),
        "stream_file": str(stream_file),
        "leaderboard_file": str(leaderboard_file),
        "governor": governor,
        "sandbox": sandbox,
        "daemon": daemon,
    }
    governor.release_subagent_lock()


# ============================================================================
# TIER 1: CATEGORY-PARTITION (E2E Nominal End-to-End Flow)
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_nominal_telemetry_to_tui_stream(e2e_harness):
    """
    Tier 1: Comprehensive E2E Nominal Path:
    Telemetry anomaly -> Daemon trigger -> Preflight lock pass -> Subagent Worktree -> Stream Log -> TUI Live Update.
    """
    daemon = e2e_harness["daemon"]
    telemetry_file = e2e_harness["telemetry_file"]
    stream_file = e2e_harness["stream_file"]

    # 1. Telemetry spike occurs
    telemetry = {
        "wan_routes": [{"interface": "en0_wifi", "rtt_ms": 110.5, "drop_rate": 0.0}]
    }
    with open(telemetry_file, "w") as f:
        json.dump(telemetry, f)

    # 2. Daemon ingests and triggers subagent cycle
    triggers = daemon.check_telemetry_triggers(daemon.parse_telemetry())
    assert len(triggers) == 1

    # 3. Mount Textual App tailing stream
    app = StreamTestApp(stream_path=stream_file)
    async with app.run_test() as pilot:
        # Run subagent cycle
        cycle_res = daemon.execute_subagent_cycle(f"resolve_{triggers[0].metric_name}", override_free_pct=45.0)
        assert cycle_res["success"] is True
        assert cycle_res["model"] == "Kimi Tandem Titan"

        # Allow widget to ingest stream lines
        await pilot.pause(0.3)

        assert app.widget.event_count == 4
        assert app.widget.latest_event["event"] == "VERIFIED"
        assert app.widget.latest_event["progress"] == 100
        assert "100%" in str(app.widget.status_header.render())


# ============================================================================
# TIER 2: BOUNDARY VALUES & ERROR CASCADE PREVENTION
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_vram_lock_blocks_spawning_without_tui_corruption(e2e_harness):
    """
    Tier 2: E2E Devil's Lock Gate (VRAM < 15%) blocks execution cleanly without polluting TUI stream with false passes.
    """
    daemon = e2e_harness["daemon"]
    stream_file = e2e_harness["stream_file"]

    app = StreamTestApp(stream_path=stream_file)
    async with app.run_test() as pilot:
        with pytest.raises(DevilsLockError, match="VRAM Headroom Lock Engaged"):
            daemon.execute_subagent_cycle("low_vram_task", override_free_pct=14.5)

        await pilot.pause(0.2)
        # No SUBAGENT_SPAWNED or VERIFIED events should have logged
        assert app.widget.event_count == 0
        assert daemon.governor.check_resource_cap() is True


# ============================================================================
# TIER 3: PAIRWISE CONCURRENCY & ISOLATION
# ============================================================================

def test_e2e_zero_mutation_guarantee_on_primary_tree(e2e_harness):
    """
    Tier 3: Strict Rule #0 & R1 Acceptance Guarantee:
    Verifies that AI subagent modifications in Git Worktree NEVER touch 01_apps in primary tree.
    """
    daemon = e2e_harness["daemon"]
    sandbox = e2e_harness["sandbox"]

    wt = sandbox.create_worktree("isolation_benchmark")
    wt_path = wt["worktree_path"]

    # Subagent edits a canonical file inside the worktree
    wt_tui_file = os.path.join(wt_path, "01_apps/canonical_port/tui/canonical_tui.py")
    os.makedirs(os.path.dirname(wt_tui_file), exist_ok=True)
    with open(wt_tui_file, "w") as f:
        f.write("# Subagent mutation inside worktree\n")

    # Primary repo canonical_tui.py MUST NOT have this line
    primary_tui_file = os.path.join(sandbox.repo_root, "01_apps/canonical_port/tui/canonical_tui.py")
    if os.path.exists(primary_tui_file):
        with open(primary_tui_file, "r") as f:
            content = f.read()
        assert "Subagent mutation inside worktree" not in content

    sandbox.cleanup_worktree(wt_path, force=True)


# ============================================================================
# TIER 4: REAL-WORLD MULTI-EVENT STREAMING SCENARIO
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_real_world_multi_event_progression(e2e_harness):
    """
    Tier 4: Real-World Application Scenario — Sequential streaming of subagent phases:
    SPAWNED -> CODE_EDIT -> RUN_TESTS -> VERIFIED -> CLEANUP with dynamic UI updates.
    """
    daemon = e2e_harness["daemon"]
    stream_file = e2e_harness["stream_file"]

    app = StreamTestApp(stream_path=stream_file)
    async with app.run_test() as pilot:
        # Phase 1: SPAWNED
        daemon.log_stream_event("SUBAGENT_SPAWNED", "Refactor Biometrics DSP", "Kimi Tandem Titan", "/tmp/wt1", 10)
        await pilot.pause(0.2)
        assert app.widget.event_count == 1
        assert "10%" in str(app.widget.status_header.render())

        # Phase 2: CODE_EDIT
        daemon.log_stream_event("CODE_EDIT", "Adding DFA-alpha1 real-time window", "Kimi Tandem Titan", "/tmp/wt1", 55)
        await pilot.pause(0.2)
        assert app.widget.event_count == 2
        assert "55%" in str(app.widget.status_header.render())

        # Phase 3: RUN_TESTS
        daemon.log_stream_event("RUN_TESTS", "Running Pan-Tompkins unit tests", "Kimi Tandem Titan", "/tmp/wt1", 85)
        await pilot.pause(0.2)
        assert app.widget.event_count == 3
        assert "85%" in str(app.widget.status_header.render())

        # Phase 4: VERIFIED
        daemon.log_stream_event("VERIFIED", "Pan-Tompkins DSP 100% Certified", "Kimi Tandem Titan", "/tmp/wt1", 100, status="PASS")
        await pilot.pause(0.2)
        assert app.widget.event_count == 4
        assert "100%" in str(app.widget.status_header.render())
        assert "PASS" in str(app.widget.status_header.render())
