"""
================================================================================
🥋 Test Suite: Interactive AI Grappling Arena & Roll Exchange Protocol (REP)
================================================================================
Test Module: tests/test_showrunner_grappling_arena.py
Subsystem: 01_apps/lauburu_showrunner
Features Tested:
1. Authentic 3,044-node OPML martial technique graph parsing & indexing
2. MediaPipe 33-landmark joint torque kinematics & 45.0 N·m safety tap gate
3. Movesense 512Hz ECG / IMU / Zone 2 Biometric Profile Bridge (Rule #0 compliant)
4. Roll Exchange Protocol (REP) digital twin sparring director & match engine
5. Bradley-Terry ELO rating calculations & Tri-Vault crystallization
6. FastAPI REST endpoints (/api/arena/*)
================================================================================
"""

import sys
import json
import pytest
from pathlib import Path
from starlette.testclient import TestClient

# Add src to sys.path
TEST_DIR = Path(__file__).resolve().parent
APP_DIR = TEST_DIR.parent
SRC_DIR = APP_DIR / "src"
BACKEND_DIR = APP_DIR / "backend"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import engine
from grappling_arena import (
    opml_tactical_graph,
    biometric_bridge,
    combat_director,
    PositionState,
    MatchState,
    FighterBiometrics
)


# ---------------------------------------------------------------------------
# 1. 3,044-Node OPML Martial Technique Graph & Kinematics Tests
# ---------------------------------------------------------------------------
def test_opml_graph_verification():
    summary = opml_tactical_graph.get_summary()
    assert summary["total_opml_nodes"] == 3044
    assert len(summary["positions_covered"]) == 9
    assert summary["critical_tap_threshold_nm"] == 45.0
    assert summary["lever_arm_meters"] == 0.35

    # Check branches
    branches = summary["branches"]
    assert "Wrestling" in branches or "Guard" in branches

    # Transitions from Guard Closed
    gc_transitions = opml_tactical_graph.get_admissible_transitions(PositionState.GUARD_CLOSED)
    assert len(gc_transitions) >= 3
    action_names = [t.name for t in gc_transitions]
    assert any("Armlock" in a or "Triangle" in a or "Sweep" in a for a in action_names)


def test_biomechanical_joint_torque_tap_gate():
    # Test safe angle
    tq_safe = opml_tactical_graph.compute_joint_torque(joint_angle_deg=30.0, limb_mass_kg=4.2, grip_leverage=1.0)
    assert tq_safe["tap_danger"] is False
    assert "SAFE" in tq_safe["risk_state"]
    assert tq_safe["torque_nm"] < 45.0

    # Test critical hyperextension (> 45.0 N·m)
    tq_crit = opml_tactical_graph.compute_joint_torque(joint_angle_deg=85.0, limb_mass_kg=4.2, grip_leverage=3.5, submission_multiplier=1.2)
    assert tq_crit["tap_danger"] is True
    assert "CRITICAL" in tq_crit["risk_state"]
    assert tq_crit["torque_nm"] >= 45.0
    assert opml_tactical_graph.is_tap_gate_triggered(tq_crit["torque_nm"]) is True


# ---------------------------------------------------------------------------
# 2. Movesense 512Hz ECG / IMU Biometrics & Rule #0 Invariants
# ---------------------------------------------------------------------------
def test_biometric_profile_bridge_rule_0():
    bio = biometric_bridge.get_live_biometrics()
    assert isinstance(bio, FighterBiometrics)
    assert bio.max_stamina_joules == 50000.0

    # In standby (when live Movesense hardware isn't attached), verify clean waiting states
    if not bio.sensor_connected:
        assert bio.heart_rate_bpm is None or isinstance(bio.heart_rate_bpm, float)
        assert "STANDBY" in bio.status or "VERIFIED_ACTIVE" in bio.status

    # Test stamina burn and recharge dynamics
    biometric_bridge.reset_stamina()
    pct_after_burn = biometric_bridge.apply_match_tick_exertion(duration_s=5.0, exertion_level="SCRAMBLE")
    assert pct_after_burn < 100.0
    assert pct_after_burn > 90.0

    biometric_bridge.reset_stamina()
    bio_reset = biometric_bridge.get_live_biometrics()
    assert bio_reset.stamina_pct == 100.0


# ---------------------------------------------------------------------------
# 3. Combat Director & Roll Exchange Protocol (REP) Match Engine
# ---------------------------------------------------------------------------
def test_combat_director_roster_and_match():
    roster = combat_director.get_roster()
    assert len(roster) >= 5
    fighter_ids = [f["id"] for f in roster]
    assert "aaron_twin" in fighter_ids
    assert "apex_npu" in fighter_ids
    assert "nyx_npu" in fighter_ids
    assert "sovereign_qwen" in fighter_ids
    assert "nexus_core" in fighter_ids

    # Create match
    match = combat_director.create_match("aaron_twin", "apex_npu", duration_s=60.0)
    assert match.state == MatchState.SPARRING
    assert match.fighter_a.id == "aaron_twin"
    assert match.fighter_b.id == "apex_npu"
    assert match.fighter_a.tatami_x == -1.2
    assert match.fighter_b.tatami_x == 1.2
    assert match.elapsed_time_s == 0.0

    # Execute a tactical tick
    res = combat_director.execute_match_tick(dt_s=5.0)
    assert res["status"] in ["MATCH_ACTIVE", "MATCH_CONCLUDED"]
    assert "latest_event" in res
    assert "tatami_coordinates" in res["latest_event"]
    assert len(res["latest_event"]["tatami_coordinates"]) == 2


def test_combat_director_full_simulation_and_elo():
    initial_aaron_elo = combat_director.fighters["aaron_twin"].elo_rating
    initial_apex_elo = combat_director.fighters["apex_npu"].elo_rating

    # Create and run match to completion
    match = combat_director.create_match("aaron_twin", "apex_npu", duration_s=30.0)
    ticks = 0
    while match.state == MatchState.SPARRING and ticks < 20:
        combat_director.execute_match_tick(dt_s=5.0)
        ticks += 1

    assert match.state in [MatchState.SUBMISSION_TAP, MatchState.POINTS_DECISION, MatchState.TIME_LIMIT]
    assert match.elapsed_time_s > 0

    # Verify Bradley-Terry ELO rating change
    new_aaron_elo = combat_director.fighters["aaron_twin"].elo_rating
    new_apex_elo = combat_director.fighters["apex_npu"].elo_rating

    # The sum of ELO adjustments should conserve zero-sum properties (delta_a + delta_b approx 0)
    delta_a = new_aaron_elo - initial_aaron_elo
    delta_b = new_apex_elo - initial_apex_elo
    assert abs(delta_a + delta_b) < 1.0


def test_tri_vault_crystallization():
    # Verify Obsidian vault markdown file exists for crystallized matches
    obsidian_files = list(Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES").glob("ARENA_MATCH_*.md"))
    assert len(obsidian_files) >= 1

    # Verify LoRA dataset contains arena record
    lora_file = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/grappling_arena_matches.jsonl")
    assert lora_file.exists()
    with open(lora_file, "r") as f:
        lines = f.readlines()
    assert len(lines) >= 1
    last_record = json.loads(lines[-1])
    assert last_record["source"] == "grappling_arena_rep"
    assert "match_id" in last_record
    assert last_record["rule_0_verified"] is True


# ---------------------------------------------------------------------------
# 4. FastAPI REST Endpoints Tests (/api/arena/*)
# ---------------------------------------------------------------------------
def test_arena_fastapi_endpoints():
    client = TestClient(engine.app)

    # 1. GET /api/arena/status
    resp = client.get("/api/arena/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACTIVE_ARENA_READY"
    assert data["opml_graph"]["total_opml_nodes"] == 3044
    assert data["protocol"] == "Roll Exchange Protocol (REP v1.0)"
    assert data["canvas_size_meters"] == 10.0
    assert data["critical_tap_threshold_nm"] == 45.0

    # 2. GET /api/arena/fighters
    resp = client.get("/api/arena/fighters")
    assert resp.status_code == 200
    fighters = resp.json()["fighters"]
    assert len(fighters) >= 5

    # 3. GET /api/arena/biometrics
    resp = client.get("/api/arena/biometrics")
    assert resp.status_code == 200
    bio_data = resp.json()
    assert "current_stamina_joules" in bio_data
    assert "max_stamina_joules" in bio_data
    assert bio_data["max_stamina_joules"] == 50000.0

    # 4. POST /api/arena/match/start
    resp = client.post("/api/arena/match/start", json={
        "fighter_a": "aaron_twin",
        "fighter_b": "nyx_npu",
        "duration_s": 120.0
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
    assert resp.json()["match"]["fighter_b"]["id"] == "nyx_npu"

    # 5. POST /api/arena/match/tick
    resp = client.post("/api/arena/match/tick", json={"dt_s": 5.0})
    assert resp.status_code == 200
    tick_data = resp.json()
    assert tick_data["status"] in ["MATCH_ACTIVE", "MATCH_CONCLUDED"]
    assert "latest_event" in tick_data

    # 6. POST /api/arena/match/simulate_full
    resp = client.post("/api/arena/match/simulate_full", json={
        "fighter_a": "sovereign_qwen",
        "fighter_b": "nexus_core",
        "duration_s": 30.0
    })
    assert resp.status_code == 200
    sim_data = resp.json()
    assert sim_data["status"] == "SUCCESS"
    assert sim_data["match"]["state"] in ["SUBMISSION_TAP", "POINTS_DECISION", "TIME_LIMIT"]
    assert sim_data["ticks_executed"] > 0

    # 7. GET /api/arena/leaderboard
    resp = client.get("/api/arena/leaderboard")
    assert resp.status_code == 200
    lb = resp.json()["leaderboard"]
    assert len(lb) >= 5
    # Verify rankings are strictly ordered descending by ELO rating
    for i in range(len(lb) - 1):
        assert lb[i]["elo_rating"] >= lb[i+1]["elo_rating"]

    # 8. POST /api/arena/match/directive (Corner Coaching)
    resp = client.post("/api/arena/match/directive", json={
        "fighter_id": "aaron_twin",
        "directive": "CONSERVE_ZONE_2"
    })
    assert resp.status_code == 200
    dir_data = resp.json()
    assert dir_data["status"] == "SUCCESS"
    assert dir_data["active_directive"] == "CONSERVE_ZONE_2"

    # 9. GET /api/arena/analysis/user (Comprehensive AI Profile)
    resp = client.get("/api/arena/analysis/user?fighter_id=aaron_twin")
    assert resp.status_code == 200
    prof = resp.json()
    assert prof["fighter_id"] == "aaron_twin"
    assert "composite_level" in prof
    assert prof["composite_level"] > 0
    assert "conditioning" in prof
    assert "grappling" in prof
    assert prof["conditioning"]["conditioning_tier"].startswith("TIER")
    assert "belt_rank" in prof["grappling"]
    assert "stripes" in prof["grappling"]
    assert prof["grappling"]["belt_rank"] in ["WHITE BELT", "BLUE BELT", "PURPLE BELT", "BROWN BELT", "BLACK BELT"]


# ---------------------------------------------------------------------------
# 5. Interactive Corner Coaching & AI Profile Unit Tests
# ---------------------------------------------------------------------------
def test_corner_coaching_directives():
    combat_director.create_match("aaron_twin", "apex_npu", duration_s=120.0)

    # Apply HUNT_SUBMISSION
    res = combat_director.apply_corner_directive(match_id=None, fighter_id="aaron_twin", directive="HUNT_SUBMISSION")
    assert res["status"] == "SUCCESS"
    assert combat_director.fighters["aaron_twin"].active_directive == "HUNT_SUBMISSION"

    # Apply SCRAMBLE_ESCAPE to defender
    res_def = combat_director.apply_corner_directive(match_id=None, fighter_id="apex_npu", directive="SCRAMBLE_ESCAPE")
    assert res_def["status"] == "SUCCESS"
    assert combat_director.fighters["apex_npu"].active_directive == "SCRAMBLE_ESCAPE"

    # Tick match with active directives
    tick_res = combat_director.execute_match_tick(dt_s=5.0)
    assert tick_res["status"] == "MATCH_ACTIVE"

    # Reset directive
    res_reset = combat_director.apply_corner_directive(match_id=None, fighter_id="aaron_twin", directive="RESET_NEUTRAL")
    assert res_reset["status"] == "SUCCESS"
    assert combat_director.fighters["aaron_twin"].active_directive is None


def test_comprehensive_user_ai_profile():
    profile = combat_director.get_user_comprehensive_profile("aaron_twin")
    assert profile["fighter_id"] == "aaron_twin"
    assert "composite_level" in profile
    assert profile["composite_level"] >= 40.0
    assert profile["conditioning"]["stamina_capacity_joules"] >= 35000.0
    assert profile["grappling"]["overall_ability_score"] >= 70.0
    assert profile["grappling"]["belt_rank"] in ["PURPLE BELT", "BROWN BELT", "BLACK BELT"]
    assert profile["grappling"]["stripes"] in [0, 1, 2, 3, 4]
    assert "tactical_archetype" in profile["grappling"]

