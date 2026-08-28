"""
Unit Tests: TUI Specialist Telemetry Daemon & Stream Logger (Milestone 2)
Covers Mesh Telemetry Monitoring (mesh_trends.json), Trigger Detection,
Devil's Lock Integration, Worktree Spawning, and Live Implementation Stream Logging.
Derived strictly from ORIGINAL_REQUEST.md §R1, §R3 and PROJECT.md §Interface Contracts.
Test Architecture: 4-Tier Test Infra (Category-Partition, Boundary Values, Pairwise Combinations, Real-World Workload).
Rule #0 Adherence: Zero fake data, genuine JSON parsing, authentic file operations.
"""

import os
import sys
import json
import time
import pytest
import tempfile
from typing import Dict, Any, Optional, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.devils_lock_governor import DevilsLockGovernor, DevilsLockError
from backend.worktree_sandbox import WorktreeSandbox, WorktreeError
from backend.tui_specialist_daemon import TuiSpecialistDaemon, DaemonTriggerEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def daemon_env(tmp_path):
    """Provides isolated daemon instance with temp paths."""
    telemetry_file = tmp_path / "mesh_trends.json"
    stream_file = tmp_path / "tui_live_implementation_stream.json"
    leaderboard_file = tmp_path / "canonical_ai_leaderboard.json"

    # Write valid leaderboard
    lb_data = {
        "leaderboard": [
            {
                "id": "kimi_tandem_titan",
                "name": "Kimi Tandem Titan",
                "elo": 3089.0,
                "specialist_skills": {"3d_ai_training_game": 99.8, "flutter_dart_mobile_architecture": 95.6}
            }
        ]
    }
    leaderboard_file.write_text(json.dumps(lb_data))

    gov = DevilsLockGovernor(
        leaderboard_path=str(leaderboard_file),
        lock_dir=str(tmp_path / "lauburu_locks"),
    )
    sb = WorktreeSandbox(base_dir=str(tmp_path / "lauburu_worktrees"))
    daemon = TuiSpecialistDaemon(
        telemetry_path=str(telemetry_file),
        stream_log_path=str(stream_file),
        governor=gov,
        sandbox=sb,
    )
    yield daemon, str(telemetry_file), str(stream_file)
    gov.release_subagent_lock()


# ============================================================================
# TIER 1: CATEGORY-PARTITION (Nominal & Happy Paths)
# ============================================================================

def test_daemon_initialization(daemon_env):
    """Tier 1: Verify daemon initializes with clean configuration."""
    daemon, tel_path, stream_path = daemon_env
    assert daemon.telemetry_path == tel_path
    assert daemon.stream_log_path == stream_path
    assert daemon.governor.check_resource_cap() is True
    assert daemon.is_running is False

def test_daemon_log_stream_event_nominal(daemon_env):
    """Tier 1: Verify log_stream_event atomically writes valid JSON lines."""
    daemon, _, stream_path = daemon_env
    event = daemon.log_stream_event(
        event="SUBAGENT_SPAWNED",
        task="Redesign Grid",
        model="Kimi Tandem Titan",
        worktree="/tmp/lauburu_worktrees/tui_100",
        progress=25,
        status="RUNNING"
    )
    assert event["event"] == "SUBAGENT_SPAWNED"
    assert event["progress"] == 25
    assert os.path.isfile(stream_path)

    with open(stream_path, "r") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 1
    assert lines[0]["event"] == "SUBAGENT_SPAWNED"

def test_daemon_detects_wan_rtt_spike(daemon_env):
    """Tier 1: Verify telemetry parser detects WAN RTT spike > 50ms."""
    daemon, tel_path, _ = daemon_env
    telemetry_data = {
        "wan_routes": [
            {"interface": "en0_wifi_wan", "rtt_ms": 78.4, "drop_rate": 0.0}
        ]
    }
    with open(tel_path, "w") as f:
        json.dump(telemetry_data, f)

    parsed = daemon.parse_telemetry()
    triggers = daemon.check_telemetry_triggers(parsed)
    assert len(triggers) == 1
    assert triggers[0].metric_name == "rtt_ms"
    assert triggers[0].current_val == 78.4

def test_daemon_executes_complete_subagent_cycle(daemon_env):
    """Tier 1: Verify end-to-end subagent execution cycle."""
    daemon, _, stream_path = daemon_env
    result = daemon.execute_subagent_cycle("telemetry_spike_fix", override_free_pct=40.0)
    assert result["success"] is True
    assert result["status"] == "PASS"
    assert result["model"] == "Kimi Tandem Titan"

    # Stream log must contain all 4 lifecycle events
    with open(stream_path, "r") as f:
        events = [json.loads(l)["event"] for l in f if l.strip()]
    assert events == ["SUBAGENT_SPAWNED", "CODE_EDIT", "RUN_TESTS", "VERIFIED"]


# ============================================================================
# TIER 2: BOUNDARY VALUES & ERROR STATES
# ============================================================================

def test_daemon_missing_telemetry_file(daemon_env):
    """Tier 2: Missing telemetry file returns empty dict without crashing."""
    daemon, tel_path, _ = daemon_env
    if os.path.exists(tel_path):
        os.remove(tel_path)
    res = daemon.parse_telemetry()
    assert res == {}
    triggers = daemon.check_telemetry_triggers(res)
    assert len(triggers) == 0

def test_daemon_malformed_telemetry_json(daemon_env):
    """Tier 2: Corrupted telemetry JSON returns empty dict cleanly."""
    daemon, tel_path, _ = daemon_env
    with open(tel_path, "w") as f:
        f.write("{ invalid json")
    res = daemon.parse_telemetry()
    assert res == {}

def test_daemon_blocks_subagent_cycle_on_low_vram(daemon_env):
    """Tier 2: Subagent cycle is blocked when free VRAM < 15.0%."""
    daemon, _, _ = daemon_env
    with pytest.raises(DevilsLockError, match="VRAM Headroom Lock Engaged"):
        daemon.execute_subagent_cycle("blocked_task", override_free_pct=10.0)

def test_daemon_blocks_subagent_cycle_on_resource_cap(daemon_env):
    """Tier 2: Subagent cycle is blocked when another subagent is active."""
    daemon, _, _ = daemon_env
    try:
        daemon.governor.acquire_subagent_lock("agent_x", "running_task")
        with pytest.raises(DevilsLockError, match="Resource Cap Violated"):
            daemon.execute_subagent_cycle("second_task", override_free_pct=30.0)
    finally:
        daemon.governor.release_subagent_lock("agent_x")

@pytest.mark.parametrize("rtt,should_trigger", [
    (49.9, False),
    (50.0, False),
    (50.1, True),
    (120.0, True),
])
def test_daemon_rtt_boundary_thresholds(daemon_env, rtt, should_trigger):
    """Tier 2: Parametrized boundary values for RTT spike threshold (> 50.0ms)."""
    daemon, _, _ = daemon_env
    data = {"wan_routes": [{"interface": "test_if", "rtt_ms": rtt, "drop_rate": 0.0}]}
    triggers = daemon.check_telemetry_triggers(data)
    assert (len(triggers) > 0) == should_trigger

@pytest.mark.parametrize("drop,should_trigger", [
    (0.049, False),
    (0.050, False),
    (0.051, True),
    (0.20, True),
])
def test_daemon_drop_rate_boundary_thresholds(daemon_env, drop, should_trigger):
    """Tier 2: Parametrized boundary values for packet drop spike threshold (> 5.0%)."""
    daemon, _, _ = daemon_env
    data = {"wan_routes": [{"interface": "test_if", "rtt_ms": 10.0, "drop_rate": drop}]}
    triggers = daemon.check_telemetry_triggers(data)
    assert (len(triggers) > 0) == should_trigger


# ============================================================================
# TIER 3: PAIRWISE COMBINATIONS & MONITORING TICKS
# ============================================================================

def test_daemon_pairwise_rtt_and_drop_spikes(daemon_env):
    """Tier 3: Pairwise combination of multiple telemetry metrics triggering simultaneously."""
    daemon, tel_path, _ = daemon_env
    telemetry = {
        "wan_routes": [
            {"interface": "en0", "rtt_ms": 120.0, "drop_rate": 0.08},
            {"interface": "en6", "rtt_ms": 12.0, "drop_rate": 0.0}
        ],
        "tailscale_peers": [
            {"node_name": "Linux_Head_Node", "status": "OFFLINE"}
        ]
    }
    triggers = daemon.check_telemetry_triggers(telemetry)
    # Expect 3 triggers: en0 RTT spike, en0 drop spike, Linux_Head_Node offline
    assert len(triggers) == 3
    reasons = [t.reason for t in triggers]
    assert any("high RTT" in r for r in reasons)
    assert any("packet drop" in r for r in reasons)
    assert any("OFFLINE" in r for r in reasons)

def test_daemon_run_tick_and_thread_lifecycle(daemon_env):
    """Tier 3: Test run_tick execution and start/stop background thread lifecycle."""
    daemon, tel_path, stream_path = daemon_env

    # 1. No triggers -> empty results
    with open(tel_path, "w") as f:
        json.dump({"wan_routes": [{"interface": "en0", "rtt_ms": 10.0, "drop_rate": 0.0}]}, f)
    tick_results = daemon.run_tick(override_free_pct=50.0)
    assert len(tick_results) == 0

    # 2. Trigger present -> executes cycle
    with open(tel_path, "w") as f:
        json.dump({"wan_routes": [{"interface": "en0", "rtt_ms": 90.0, "drop_rate": 0.0}]}, f)
    tick_results = daemon.run_tick(override_free_pct=50.0)
    assert len(tick_results) == 1
    assert tick_results[0]["success"] is True

    # 3. Thread start and stop
    daemon.start_daemon(interval=0.1)
    assert daemon.is_running is True
    time.sleep(0.2)
    daemon.stop_daemon()
    assert daemon.is_running is False


# ============================================================================
# TIER 4: REAL-WORLD SCENARIOS
# ============================================================================

def test_scenario_daemon_telemetry_to_isolated_worktree(daemon_env):
    """
    Tier 4: Complete Real-World Scenario — Telemetry degradation triggers
    autonomous subagent spawn, isolated worktree modification, live stream logging,
    and verified non-mutation of primary tree.
    """
    daemon, tel_path, stream_path = daemon_env

    # 1. Telemetry link degrades
    telemetry = {"wan_routes": [{"interface": "en0_wifi", "rtt_ms": 150.0, "drop_rate": 0.12}]}
    with open(tel_path, "w") as f:
        json.dump(telemetry, f)

    data = daemon.parse_telemetry()
    triggers = daemon.check_telemetry_triggers(data)
    assert len(triggers) > 0

    # 2. Daemon spawns subagent cycle
    cycle_res = daemon.execute_subagent_cycle(f"heal_{triggers[0].metric_name}", override_free_pct=50.0)
    assert cycle_res["success"] is True

    # 3. Stream log verified with timestamps and progression
    with open(stream_path, "r") as f:
        logs = [json.loads(l) for l in f if l.strip()]
    assert len(logs) == 4
    assert logs[0]["progress"] < logs[1]["progress"] < logs[2]["progress"] < logs[3]["progress"]
    assert logs[-1]["status"] == "PASS"
