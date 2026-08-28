#!/usr/bin/env python3
"""
tests/test_adversarial_nomad_roi_governor.py
=============================================
Adversarial Stress Harness & Empirical Verification for Nomad ROI Cron Governor (v4.0).

Challenger Test Dimensions:
1. Mathematical ROI Engine Stress (boundary runs, durations, extreme CPU/RAM, non-linear failure penalties, clamping)
2. Cadence Elasticity State Machine Stress (port closures, packet loss spikes, rapid triage recovery, circuit breaker latching)
3. Remote SSH Offloading & Graceful Degradation Stress (unreachable IPs, auth timeouts, corrupted payloads, hierarchy fallback)
4. Governor Lifecycle & Subprocess Fault Injection Stress (concurrency, bad JSON recovery, signal terminations)
"""

import os
import sys
import json
import math
import time
import socket
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/automation"))

from nomad_roi_cron_governor import (
    DynamicEmpiricalROIEngine,
    AdaptiveCadenceElasticity,
    RemoteSSHWorkerDispatcher,
    AutonomousRemediationPipeline,
    LoRADecisionTracer,
    NomadROICronGovernor,
    PORTFOLIO_FILE,
    LEDGER_FILE,
    MASTER_LEDGER_JSONL,
    LORA_DECISIONS_JSONL,
    DASHBOARD_FILE,
    LOCAL_DASHBOARD_FILE,
    GOVERNOR_STATUS_FILE,
    REMOTE_NODES,
    DEFAULT_JOBS
)


# ==============================================================================
# SECTION 1: MATHEMATICAL ROI ENGINE ADVERSARIAL STRESS HARNESS
# ==============================================================================

class TestAdversarialMathematicalROIEngine:
    """Stress tests mathematical stability, monotonic properties, and boundary clamping."""

    @pytest.mark.parametrize("runs,successes", [
        (0, 0),
        (1, 0),
        (1, 1),
        (10, 5),
        (100, 100),
        (1000, 999),
        (100000, 99999),
        (1000000, 1000000),
        (-5, -5), # Negative edge input
        (10, 20), # Successes > total runs edge input
    ])
    def test_bayesian_success_rate_boundary_and_fuzz(self, runs, successes):
        rate = DynamicEmpiricalROIEngine.compute_bayesian_success_rate(successes, runs)
        assert 0.0 <= rate <= 1.0, f"Bayesian rate out of bounds for runs={runs}, successes={successes}: {rate}"
        if runs >= 0:
            assert rate > 0.0 and rate < 1.0

    @pytest.mark.parametrize("duration", [
        0.0,
        0.00001,
        0.0001,
        0.001,
        0.1,
        1.0,
        10.0,
        60.0,
        120.0,
        600.0,
        3600.0,
        86400.0,
        -10.0,
    ])
    def test_runtime_efficiency_exponential_decay_fuzz(self, duration):
        eff = DynamicEmpiricalROIEngine.compute_runtime_efficiency(duration)
        assert 0.0 <= eff <= 1.0, f"Runtime efficiency out of [0, 1] for duration={duration}: {eff}"
        if duration >= 0.0:
            eff_longer = DynamicEmpiricalROIEngine.compute_runtime_efficiency(duration + 5.0)
            assert eff >= eff_longer

    @pytest.mark.parametrize("cpu_pct,rss_mb", [
        (0.0, 0.0),
        (0.1, 10.0),
        (50.0, 512.0),
        (100.0, 2048.0),
        (200.0, 4096.0),
        (1000.0, 65536.0),
        (-50.0, -100.0),
    ])
    def test_resource_efficiency_extreme_footprint_fuzz(self, cpu_pct, rss_mb):
        eff = DynamicEmpiricalROIEngine.compute_resource_efficiency(cpu_pct, rss_mb)
        assert 0.0 <= eff <= 1.0, f"Resource efficiency out of [0, 1] for cpu={cpu_pct}, rss={rss_mb}: {eff}"
        if cpu_pct >= 100.0 and rss_mb >= 2048.0:
            assert eff == 0.0

    @pytest.mark.parametrize("failures", list(range(0, 15)) + [20, 50, 100, -5])
    def test_consecutive_failure_penalty_non_linear_growth(self, failures):
        pen = DynamicEmpiricalROIEngine.compute_failure_penalty(failures)
        assert 0.0 <= pen <= 10.0, f"Failure penalty out of [0, 10] for failures={failures}: {pen}"
        if failures == 0 or failures < 0:
            assert pen == 0.0
        elif failures == 1:
            assert pytest.approx(pen, 0.001) == 0.85
        elif failures == 2:
            assert pytest.approx(pen, 0.001) == 0.85 * (2 ** 1.45)
        elif failures >= 6:
            assert pen == 10.0

    def test_composite_roi_monotonic_degradation_across_failure_spectrum(self):
        """Verify ROI strictly drops or stays clamped as consecutive failures increase from 0 to 10."""
        job = {
            "id": "cron_001_mesh_healer",
            "total_runs": 100,
            "successful_runs": 100,
            "consecutive_failures": 0,
            "incident_avoidance_yield": 9.85,
            "token_savings_yield": 9.50,
            "status": "ACTIVE"
        }
        telemetry = {
            "status": "SUCCESS",
            "exit_code": 0,
            "duration_sec": 0.5,
            "cpu_pct": 2.0,
            "rss_mb": 30.0
        }

        scores = []
        for f in range(11):
            job_copy = dict(job)
            job_copy["consecutive_failures"] = f
            tel_copy = dict(telemetry)
            if f > 0:
                tel_copy["status"] = "FAILED"
                tel_copy["exit_code"] = 1
            score = DynamicEmpiricalROIEngine.compute_empirical_roi(job_copy, tel_copy)
            assert 0.0 <= score <= 10.0
            scores.append(score)

        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i+1], f"ROI failed to monotonically decrease at failure {i+1}: {scores}"

    def test_composite_roi_extreme_runtimes_and_overhead(self):
        job = {"total_runs": 50, "successful_runs": 50, "consecutive_failures": 0, "status": "ACTIVE"}
        # Extreme 10-hour run
        tel_long = {"duration_sec": 36000.0, "cpu_pct": 100.0, "rss_mb": 8192.0}
        roi_long = DynamicEmpiricalROIEngine.compute_empirical_roi(job, tel_long)
        assert 0.0 <= roi_long <= 10.0
        assert roi_long < 8.0 # High resource/duration penalty applied

        # Ultra-short 0.0001s run
        tel_fast = {"duration_sec": 0.0001, "cpu_pct": 1.0, "rss_mb": 20.0}
        roi_fast = DynamicEmpiricalROIEngine.compute_empirical_roi(job, tel_fast)
        assert roi_fast >= 9.5


# ==============================================================================
# SECTION 2: CADENCE ELASTICITY STATE TRANSITIONS & FAULT INJECTION
# ==============================================================================

class TestAdversarialCadenceElasticityStateTransitions:
    """Stress tests the 4-tier state machine under artificial network and host anomalies."""

    def test_port_closure_matrix_triggers_rapid_triage(self):
        job = {
            "base_interval_sec": 900,
            "min_interval_sec": 120,
            "max_interval_sec": 1800,
            "status": "ACTIVE",
            "consecutive_failures": 0,
            "stable_runs_count": 5,
            "roi_score": 9.8
        }
        for port in [3000, 18802, 50052]:
            tel = {
                "ports_healthy": False,
                "ports_status": {str(p): (p != port) for p in [3000, 18802, 50052]},
                "packet_loss_pct": 0.0,
                "host_ram_used_pct": 40.0,
                "thermal_throttling": False,
                "battery_temp_c": 30.0
            }
            interval, tier, priority, status = AdaptiveCadenceElasticity.compute_elastic_cadence(job, tel)
            assert tier == AdaptiveCadenceElasticity.TIER_RAPID_TRIAGE
            assert interval == 180
            assert status == "ACTIVE"

    @pytest.mark.parametrize("packet_loss", [5.1, 10.0, 25.0, 50.0, 99.0, 100.0])
    def test_packet_loss_spikes_trigger_rapid_triage(self, packet_loss):
        job = {
            "base_interval_sec": 600,
            "min_interval_sec": 120,
            "max_interval_sec": 1800,
            "status": "ACTIVE",
            "consecutive_failures": 0,
            "roi_score": 9.5
        }
        tel = {
            "ports_healthy": True,
            "packet_loss_pct": packet_loss,
            "host_ram_used_pct": 40.0,
            "thermal_throttling": False,
            "battery_temp_c": 30.0
        }
        interval, tier, priority, status = AdaptiveCadenceElasticity.compute_elastic_cadence(job, tel)
        assert tier == AdaptiveCadenceElasticity.TIER_RAPID_TRIAGE
        assert interval == 120

    @pytest.mark.parametrize("ram_pct", [85.1, 90.0, 95.0, 100.0])
    def test_host_ram_pressure_triggers_rapid_triage(self, ram_pct):
        job = {
            "base_interval_sec": 1200,
            "min_interval_sec": 300,
            "max_interval_sec": 3600,
            "status": "ACTIVE"
        }
        tel = {
            "ports_healthy": True,
            "packet_loss_pct": 0.0,
            "host_ram_used_pct": ram_pct,
            "thermal_throttling": False,
            "battery_temp_c": 30.0
        }
        interval, tier, priority, status = AdaptiveCadenceElasticity.compute_elastic_cadence(job, tel)
        assert tier == AdaptiveCadenceElasticity.TIER_RAPID_TRIAGE
        assert interval == 300

    @pytest.mark.parametrize("battery_temp", [41.1, 45.0, 55.0])
    def test_battery_thermal_surge_triggers_rapid_triage(self, battery_temp):
        job = {
            "base_interval_sec": 900,
            "min_interval_sec": 120,
            "max_interval_sec": 1800,
            "status": "ACTIVE"
        }
        tel = {
            "ports_healthy": True,
            "packet_loss_pct": 0.0,
            "host_ram_used_pct": 40.0,
            "thermal_throttling": False,
            "battery_temp_c": battery_temp
        }
        interval, tier, priority, status = AdaptiveCadenceElasticity.compute_elastic_cadence(job, tel)
        assert tier == AdaptiveCadenceElasticity.TIER_RAPID_TRIAGE
        assert interval == 180

    def test_rapid_triage_to_extended_stability_backoff_lifecycle(self):
        job = {
            "id": "cron_001_mesh_healer",
            "base_interval_sec": 900,
            "min_interval_sec": 120,
            "max_interval_sec": 1800,
            "status": "ACTIVE",
            "consecutive_failures": 0,
            "stable_runs_count": 0,
            "roi_score": 9.80
        }

        healthy_tel = {
            "ports_healthy": True,
            "packet_loss_pct": 0.0,
            "host_ram_used_pct": 45.0,
            "thermal_throttling": False,
            "battery_temp_c": 30.0
        }
        int_1, tier_1, _, _ = AdaptiveCadenceElasticity.compute_elastic_cadence(job, healthy_tel)
        assert tier_1 == AdaptiveCadenceElasticity.TIER_NOMINAL
        assert int_1 == 900

        outage_tel = dict(healthy_tel)
        outage_tel["ports_healthy"] = False
        int_2, tier_2, _, _ = AdaptiveCadenceElasticity.compute_elastic_cadence(job, outage_tel)
        assert tier_2 == AdaptiveCadenceElasticity.TIER_RAPID_TRIAGE
        assert int_2 == 180

        job["stable_runs_count"] = 1
        int_3, tier_3, _, _ = AdaptiveCadenceElasticity.compute_elastic_cadence(job, healthy_tel)
        assert tier_3 == AdaptiveCadenceElasticity.TIER_NOMINAL
        assert int_3 == 900

        job["stable_runs_count"] = 10
        int_4, tier_4, _, _ = AdaptiveCadenceElasticity.compute_elastic_cadence(job, healthy_tel)
        assert tier_4 == AdaptiveCadenceElasticity.TIER_BACKOFF
        assert int_4 == 1350

        job["stable_runs_count"] = 15
        int_5, tier_5, _, _ = AdaptiveCadenceElasticity.compute_elastic_cadence(job, healthy_tel)
        assert tier_5 == AdaptiveCadenceElasticity.TIER_BACKOFF
        assert int_5 == 1575

        int_6, tier_6, _, _ = AdaptiveCadenceElasticity.compute_elastic_cadence(job, {"ports_healthy": True, "packet_loss_pct": 12.0})
        assert tier_6 == AdaptiveCadenceElasticity.TIER_RAPID_TRIAGE
        assert int_6 == 180

    def test_circuit_breaker_stopped_terminal_state(self):
        job = {
            "base_interval_sec": 900,
            "min_interval_sec": 120,
            "max_interval_sec": 3600,
            "consecutive_failures": 5,
            "status": "ACTIVE"
        }
        tel = {"ports_healthy": True, "packet_loss_pct": 0.0}
        interval, tier, priority, status = AdaptiveCadenceElasticity.compute_elastic_cadence(job, tel)
        assert tier == AdaptiveCadenceElasticity.TIER_CIRCUIT_BREAKER
        assert status == "STOPPED"
        assert priority == "DECOMMISSIONED_LOW_ROI"
        assert interval == 3600


# ==============================================================================
# SECTION 3: SSH OFFLOADING, NETWORK TIMEOUTS & GRACEFUL DEGRADATION
# ==============================================================================

class TestAdversarialSSHOffloadingAndGracefulFallback:
    """Stress tests remote SSH failure modes, payload corruptions, and local fallback."""

    def test_unreachable_ip_triggers_local_fallback(self):
        gov = NomadROICronGovernor()
        job_info = gov.portfolio["jobs"]["cron_004_nomad_scout_and_debate"]
        job_info["execution_target"] = "remote_ssh"
        job_info["preferred_node"] = "linux_head_node"
        job_info["fallback_node"] = "macbook_air"
        job_info["fallback_to_local"] = True
        job_info["last_run"] = 0

        with patch.object(RemoteSSHWorkerDispatcher, "is_node_reachable", return_value=False), \
             patch.object(gov, "_execute_local", return_value=({"status": "SUCCESS", "exit_code": 0, "duration_sec": 0.45, "cpu_pct": 2.0, "rss_mb": 30.0}, True)) as mock_local:
            executed = gov.execute_job_if_due("cron_004_nomad_scout_and_debate", job_info, current_time=time.time())
            assert executed is True
            assert mock_local.called
            assert "fallback" in job_info["offload_node"]
            assert job_info["consecutive_failures"] == 0

    def test_ssh_auth_and_connect_timeout_handling(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=3)):
            res = RemoteSSHWorkerDispatcher.dispatch_remote_job("linux_head_node", "fake_script.py", timeout=3)
            assert res["status"] == "TIMEOUT"
            assert res["exit_code"] == 124
            assert res["offload_node"] == "linux_head_node"
            assert "timed out" in res["error"]

    def test_ssh_unhandled_subprocess_exception_handling(self):
        with patch("subprocess.run", side_effect=OSError("Network is unreachable")):
            res = RemoteSSHWorkerDispatcher.dispatch_remote_job("linux_head_node", "fake_script.py")
            assert res["status"] == "ERROR"
            assert res["exit_code"] == 1
            assert "Network is unreachable" in res["error"]

    @pytest.mark.parametrize("corrupted_stdout,exit_code,expected_status", [
        ("NOT_JSON_AT_ALL\nRandom bash warning: warning\n", 0, "SUCCESS"),
        ("{incomplete_json: true", 0, "SUCCESS"),
        ("Segmentation fault (core dumped)\n", 139, "FAILED"),
        ("Killed: 9\n", 137, "FAILED"),
        ("", 0, "SUCCESS"),
        ("", 1, "FAILED"),
        ("{\"status\": \"SUCCESS\", \"duration_sec\": 3.5, \"cpu_pct\": 12.0, \"rss_mb\": 120.0, \"tokens_saved\": 50000.0, \"usd_saved\": 0.10}", 0, "SUCCESS"),
    ])
    def test_ssh_corrupted_response_parsing_resilience(self, corrupted_stdout, exit_code, expected_status):
        telemetry = RemoteSSHWorkerDispatcher.parse_remote_telemetry(
            stdout=corrupted_stdout,
            stderr="Some stderr message" if exit_code != 0 else "",
            duration=1.5,
            exit_code=exit_code,
            node_key="linux_head_node"
        )
        assert telemetry["status"] == expected_status
        assert telemetry["exit_code"] == exit_code
        assert "offload_node" in telemetry
        assert telemetry["duration_sec"] > 0

    def test_target_node_selection_priority_order(self):
        job = {
            "preferred_node": "linux_head_node",
            "fallback_node": "macbook_air"
        }

        # Case 1: Preferred reachable
        with patch.object(RemoteSSHWorkerDispatcher, "is_node_reachable", side_effect=lambda k, **kwargs: k == "linux_head_node"):
            node_k, _ = RemoteSSHWorkerDispatcher.select_target_node(job)
            assert node_k == "linux_head_node"

        # Case 2: Preferred down, fallback reachable
        with patch.object(RemoteSSHWorkerDispatcher, "is_node_reachable", side_effect=lambda k, **kwargs: k == "macbook_air"):
            node_k, _ = RemoteSSHWorkerDispatcher.select_target_node(job)
            assert node_k == "macbook_air"

        # Case 3: Preferred and fallback down, MacBook Pro reachable
        with patch.object(RemoteSSHWorkerDispatcher, "is_node_reachable", side_effect=lambda k, **kwargs: k == "macbook_pro_vault"):
            node_k, _ = RemoteSSHWorkerDispatcher.select_target_node(job)
            assert node_k == "macbook_pro_vault"

        # Case 4: All remote nodes down -> fallback to local mac_mini_host
        with patch.object(RemoteSSHWorkerDispatcher, "is_node_reachable", return_value=False):
            node_k, _ = RemoteSSHWorkerDispatcher.select_target_node(job)
            assert node_k == "mac_mini_host"


# ==============================================================================
# SECTION 4: FULL GOVERNOR STRESS & RESILIENCE HARNESS
# ==============================================================================

class TestAdversarialGovernorLifecycleResilience:
    """Stress tests full governance cycles, corrupted files, and concurrent ledger writing."""

    def test_governor_cycle_survives_partial_script_exceptions(self):
        gov = NomadROICronGovernor()
        failing_job = gov.portfolio["jobs"]["cron_001_mesh_healer"]
        failing_job["last_run"] = 0

        with patch.object(gov, "_execute_local", return_value=({"status": "ERROR", "exit_code": 1, "duration_sec": 0.1, "error": "Fatal exception"}, False)):
            ran = gov.execute_job_if_due("cron_001_mesh_healer", failing_job, current_time=time.time())
            assert ran is True
            assert failing_job["consecutive_failures"] == 1
            assert failing_job["roi_score"] < 10.0

    def test_governor_optimization_writes_consistent_json_ledgers(self):
        gov = NomadROICronGovernor()
        gov.optimize_and_adjust_portfolio()

        assert PORTFOLIO_FILE.exists()
        with open(PORTFOLIO_FILE, "r") as f:
            port = json.load(f)
            assert "jobs" in port
            assert "system_roi_score" in port
            assert len(port["jobs"]) >= 7

        assert LEDGER_FILE.exists()
        with open(LEDGER_FILE, "r") as f:
            ledger = json.load(f)
            assert "roi_leaderboard" in ledger
            assert len(ledger["roi_leaderboard"]) >= 7

        assert MASTER_LEDGER_JSONL.exists()
        with open(MASTER_LEDGER_JSONL, "r") as f:
            for line in f:
                if line.strip():
                    ev = json.loads(line.strip())
                    assert "timestamp_utc" in ev
                    assert "event_type" in ev

    def test_governor_rapid_successive_cycles_stability(self):
        gov = NomadROICronGovernor()
        for cycle in range(10):
            status = gov.run_governance_cycle()
            assert status["status"] == "NOMAD_CRON_GOVERNOR_OPTIMAL"
            assert status["system_roi_score"] > 0.0

    def test_remediation_pipeline_progression_across_attempts(self):
        """Test the 5-tier remediation progression as failure attempts increment."""
        job = {
            "name": "Degraded Service",
            "consecutive_failures": 1,
            "remediation_attempts": 0,
            "script": str(REPO_ROOT / "06_scripts_and_tooling/network/nomad_courier_self_healer.py"),
            "remediation_config": {
                "monitored_port": 3000,
                "wol_device_key": "linux_head_node",
                "max_remediation_retries": 3,
                "escalate_to_debate": True
            }
        }
        with patch.object(AutonomousRemediationPipeline, "probe_port", return_value=False), \
             patch.object(AutonomousRemediationPipeline, "reclaim_port", return_value=True), \
             patch.object(AutonomousRemediationPipeline, "trigger_wol", return_value={"success": True}), \
             patch.object(AutonomousRemediationPipeline, "restart_daemon", return_value={"success": True, "pid": 99999}):

            # Attempt 1: Port reclaim + WoL + Daemon restart
            out_1 = AutonomousRemediationPipeline.execute_remediation("cron_001_mesh_healer", job, {"status": "FAILED"})
            assert out_1["attempts"] == 1
            assert any("PORT_RECLAIM" in a for a in out_1["actions_taken"])
            assert any("WOL" in a for a in out_1["actions_taken"])
            assert any("DAEMON_RESTART" in a for a in out_1["actions_taken"])

            # Attempt 3: Max retries reached -> Escalate to Tri-Orchestrator Debate
            job["consecutive_failures"] = 3
            job["remediation_attempts"] = 2
            with patch.object(AutonomousRemediationPipeline, "trigger_ai_debate", return_value={"consensus_reached": True}) as mock_deb:
                out_3 = AutonomousRemediationPipeline.execute_remediation("cron_001_mesh_healer", job, {"status": "FAILED"})
                assert out_3["attempts"] == 3
                assert "TIER_4_TRI_ORCHESTRATOR_DEBATE_ESCALATED" in out_3["actions_taken"]
                assert mock_deb.called

            # Attempt 5: Consecutive failures >= 5 -> Circuit Breaker
            job["consecutive_failures"] = 5
            job["remediation_attempts"] = 4
            out_5 = AutonomousRemediationPipeline.execute_remediation("cron_001_mesh_healer", job, {"status": "FAILED"})
            assert "TIER_5_CIRCUIT_BREAKER_ENGAGED" in out_5["actions_taken"]
            assert job["status"] == "STOPPED"
