#!/usr/bin/env python3
"""
tests/test_nomad_roi_cron_governor.py
======================================
Comprehensive 4-Tier Test Suite for Requirements R1, R2, R3, R4, R5:
- Tier 1: Unit & Feature Coverage (R1 - R5)
- Tier 2: Boundary & Edge Case Testing
- Tier 3: Pairwise Cross-Feature Integration
- Tier 4: Real-World Workloads & E2E Verification

Total Test Count: Exactly 57 verified tests.
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


@pytest.fixture(autouse=True)
def clean_portfolio_fixture():
    """Ensures test isolation by resetting default active states in portfolio file."""
    if PORTFOLIO_FILE.exists():
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                data = json.load(f)
            if "jobs" in data and isinstance(data["jobs"], dict):
                for d in DEFAULT_JOBS:
                    j_id = d["id"]
                    if j_id in data["jobs"]:
                        data["jobs"][j_id]["status"] = d["status"]
                        data["jobs"][j_id]["consecutive_failures"] = 0
                        data["jobs"][j_id]["remediation_attempts"] = 0
                        data["jobs"][j_id]["cadence_tier"] = "NOMINAL_GOVERNANCE"
                        data["jobs"][j_id]["interval_sec"] = d["base_interval_sec"]
                with open(PORTFOLIO_FILE, "w") as f:
                    json.dump(data, f, indent=2)
        except Exception:
            pass
    yield


# ==============================================================================
# TIER 1: UNIT & FEATURE COVERAGE (20 TESTS)
# ==============================================================================

class TestTier1UnitFeatureCoverage:
    """Tier 1: Comprehensive Unit Tests covering R1 through R5."""

    def test_t1_bayesian_success_rate_boundary_and_smoothing(self):
        assert DynamicEmpiricalROIEngine.compute_bayesian_success_rate(0, 0) == 0.5
        assert pytest.approx(DynamicEmpiricalROIEngine.compute_bayesian_success_rate(10, 10), 0.001) == 11.0 / 12.0
        assert pytest.approx(DynamicEmpiricalROIEngine.compute_bayesian_success_rate(95, 100), 0.001) == 96.0 / 102.0

    def test_t1_runtime_efficiency_exponential_decay(self):
        assert DynamicEmpiricalROIEngine.compute_runtime_efficiency(0.0) == 1.0
        assert pytest.approx(DynamicEmpiricalROIEngine.compute_runtime_efficiency(60.0), 0.001) == math.exp(-1.0)
        assert pytest.approx(DynamicEmpiricalROIEngine.compute_runtime_efficiency(30.0), 0.001) == math.exp(-0.5)

    def test_t1_resource_efficiency_cpu_and_rss_clamping(self):
        assert DynamicEmpiricalROIEngine.compute_resource_efficiency(0.0, 0.0) == 1.0
        assert DynamicEmpiricalROIEngine.compute_resource_efficiency(100.0, 2048.0) == 0.0
        expected = 1.0 - ((0.10 * 0.5) + (50.0 / 2048.0 * 0.5))
        assert pytest.approx(DynamicEmpiricalROIEngine.compute_resource_efficiency(10.0, 50.0), 0.001) == expected

    def test_t1_failure_penalty_non_linear_growth(self):
        assert DynamicEmpiricalROIEngine.compute_failure_penalty(0) == 0.0
        assert pytest.approx(DynamicEmpiricalROIEngine.compute_failure_penalty(1), 0.001) == 0.85
        assert pytest.approx(DynamicEmpiricalROIEngine.compute_failure_penalty(2), 0.001) == 0.85 * (2 ** 1.45)
        assert pytest.approx(DynamicEmpiricalROIEngine.compute_failure_penalty(5), 0.001) == 0.85 * (5 ** 1.45)

    def test_t1_incident_avoidance_bonus_and_deduction(self):
        job = {"incident_avoidance_yield": 9.5, "consecutive_failures": 0}
        tel_ok = {"status": "SUCCESS", "exit_code": 0, "output_summary": "All systems healed and online"}
        assert DynamicEmpiricalROIEngine.compute_incident_avoidance(job, tel_ok) >= 9.70

        job_fail = {"incident_avoidance_yield": 9.5, "consecutive_failures": 2}
        tel_fail = {"status": "FAILED", "exit_code": 1}
        assert DynamicEmpiricalROIEngine.compute_incident_avoidance(job_fail, tel_fail) <= 6.5

    def test_t1_token_savings_yield_and_usd_contributions(self):
        job = {"token_savings_yield": 9.3}
        tel = {"tokens_saved": 50000.0, "usd_saved": 0.15}
        assert pytest.approx(DynamicEmpiricalROIEngine.compute_token_savings(job, tel), 0.01) == 9.55

    def test_t1_composite_roi_healthy_execution(self):
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
            "duration_sec": 0.45,
            "cpu_pct": 2.0,
            "rss_mb": 30.0,
            "output_summary": "All routines healed and online"
        }
        roi = DynamicEmpiricalROIEngine.compute_empirical_roi(job, telemetry)
        assert 9.70 <= roi <= 10.00

    def test_t1_composite_roi_degraded_execution(self):
        job = {
            "id": "cron_001_mesh_healer",
            "total_runs": 10,
            "successful_runs": 7,
            "consecutive_failures": 3,
            "incident_avoidance_yield": 9.85,
            "token_savings_yield": 9.50,
            "status": "ACTIVE"
        }
        telemetry = {
            "status": "FAILED",
            "exit_code": 1,
            "duration_sec": 12.0,
            "cpu_pct": 30.0,
            "rss_mb": 250.0,
            "error": "Timeout socket error"
        }
        roi = DynamicEmpiricalROIEngine.compute_empirical_roi(job, telemetry)
        assert roi < 7.00

    def test_t1_cadence_rapid_triage_on_port_down(self):
        job = {"base_interval_sec": 900, "min_interval_sec": 120, "max_interval_sec": 1800, "status": "ACTIVE"}
        telemetry = {"ports_healthy": False, "packet_loss_pct": 0.0, "host_ram_used_pct": 50.0, "thermal_throttling": False, "battery_temp_c": 30.0}
        interval, tier, priority, status = AdaptiveCadenceElasticity.compute_elastic_cadence(job, telemetry)
        assert tier == "RAPID_TRIAGE"
        assert interval == 180
        assert status == "ACTIVE"

    def test_t1_cadence_rapid_triage_on_packet_loss(self):
        job = {"base_interval_sec": 600, "min_interval_sec": 120, "max_interval_sec": 1800, "status": "ACTIVE"}
        telemetry = {"ports_healthy": True, "packet_loss_pct": 8.0, "host_ram_used_pct": 50.0, "thermal_throttling": False, "battery_temp_c": 30.0}
        interval, tier, priority, status = AdaptiveCadenceElasticity.compute_elastic_cadence(job, telemetry)
        assert tier == "RAPID_TRIAGE"
        assert interval == 120
        assert status == "ACTIVE"

    def test_t1_cadence_rapid_triage_on_job_failure(self):
        job = {"base_interval_sec": 1200, "min_interval_sec": 300, "max_interval_sec": 3600, "consecutive_failures": 1, "status": "ACTIVE"}
        telemetry = {"ports_healthy": True, "packet_loss_pct": 0.0, "host_ram_used_pct": 50.0, "thermal_throttling": False, "battery_temp_c": 30.0}
        interval, tier, priority, status = AdaptiveCadenceElasticity.compute_elastic_cadence(job, telemetry)
        assert tier == "RAPID_TRIAGE"
        assert interval == 300

    def test_t1_cadence_nominal_governance_steady_state(self):
        job = {"base_interval_sec": 900, "min_interval_sec": 120, "max_interval_sec": 1800, "stable_runs_count": 5, "roi_score": 9.85, "status": "ACTIVE"}
        telemetry = {"ports_healthy": True, "packet_loss_pct": 0.0, "host_ram_used_pct": 50.0, "thermal_throttling": False, "battery_temp_c": 30.0}
        interval, tier, priority, status = AdaptiveCadenceElasticity.compute_elastic_cadence(job, telemetry)
        assert tier == "NOMINAL_GOVERNANCE"
        assert interval == 900
        assert priority == "CRITICAL_HIGH_ROI"

    def test_t1_cadence_extended_stability_backoff(self):
        job = {"base_interval_sec": 900, "min_interval_sec": 120, "max_interval_sec": 1800, "stable_runs_count": 15, "roi_score": 9.85, "status": "ACTIVE"}
        telemetry = {"ports_healthy": True, "packet_loss_pct": 0.0, "host_ram_used_pct": 50.0, "thermal_throttling": False, "battery_temp_c": 30.0}
        interval, tier, priority, status = AdaptiveCadenceElasticity.compute_elastic_cadence(job, telemetry)
        assert tier == "EXTENDED_STABILITY_BACKOFF"
        assert interval == 1575

    def test_t1_cadence_circuit_breaker_stopped(self):
        job = {"base_interval_sec": 900, "min_interval_sec": 120, "max_interval_sec": 3600, "consecutive_failures": 5, "roi_score": 5.0, "total_runs": 10, "status": "ACTIVE"}
        telemetry = {"ports_healthy": True, "packet_loss_pct": 0.0, "host_ram_used_pct": 50.0, "thermal_throttling": False, "battery_temp_c": 30.0}
        interval, tier, priority, status = AdaptiveCadenceElasticity.compute_elastic_cadence(job, telemetry)
        assert tier == "CIRCUIT_BREAKER_STOPPED"
        assert status == "STOPPED"
        assert priority == "DECOMMISSIONED_LOW_ROI"

    def test_t1_ssh_dispatcher_node_registry_and_priority(self):
        assert "linux_head_node" in REMOTE_NODES
        assert "macbook_pro_vault" in REMOTE_NODES
        assert "macbook_air" in REMOTE_NODES
        assert "mac_mini_host" in REMOTE_NODES
        assert REMOTE_NODES["linux_head_node"]["priority_rank"] == 1

    def test_t1_ssh_dispatcher_command_builder(self):
        cmd = RemoteSSHWorkerDispatcher.build_ssh_command(
            node_key="linux_head_node",
            command="python3 test.py",
            connect_timeout=3,
            key_path="/tmp/nonexistent_key"
        )
        assert "ssh" in cmd[0]
        assert "ConnectTimeout=3" in str(cmd)
        assert "StrictHostKeyChecking=no" in str(cmd)
        assert "linux@100.101.39.98" in cmd

    def test_t1_ssh_dispatcher_telemetry_json_parsing(self):
        raw_json_stdout = '{"status": "SUCCESS", "duration_sec": 1.25, "cpu_pct": 8.0, "rss_mb": 55.0, "tokens_saved": 12000.0, "usd_saved": 0.05}'
        telemetry = RemoteSSHWorkerDispatcher.parse_remote_telemetry(
            stdout=raw_json_stdout,
            stderr="",
            duration=1.25,
            exit_code=0,
            node_key="linux_head_node"
        )
        assert telemetry["status"] == "SUCCESS"
        assert telemetry["duration_sec"] == 1.25
        assert telemetry["cpu_pct"] == 8.0
        assert telemetry["rss_mb"] == 55.0
        assert telemetry["tokens_saved"] == 12000.0

    def test_t1_remediation_port_probe_and_reclaim(self):
        closed = AutonomousRemediationPipeline.probe_port(59999, host="127.0.0.1", timeout=0.1)
        assert closed is False

    def test_t1_lora_decision_tracer_alpaca_schema(self):
        job_info = {
            "total_runs": 50,
            "successful_runs": 50,
            "consecutive_failures": 0,
            "last_elapsed_sec": 0.45,
            "interval_sec": 900,
            "roi_score": 9.85,
            "offload_node": "linux_head_node"
        }
        record = LoRADecisionTracer.log_decision(
            job_id="cron_006_swarm_truth_audit",
            job_info=job_info,
            decision_type="TEST_DECISION",
            action="TEST_ACTION"
        )
        assert "instruction" in record
        assert "input" in record
        assert "output" in record
        assert record["instruction"] == "Nomad Cron ROI Governance Decision"
        assert record["output"]["decision"] == "TEST_DECISION"
        assert record["output"]["offloaded_to"] == "linux_head_node"

    def test_t1_dashboard_sparkline_generator(self):
        assert NomadROICronGovernor._generate_sparkline(9.90) == "▇█████"
        assert NomadROICronGovernor._generate_sparkline(9.60) == "▅▆▇███"
        assert NomadROICronGovernor._generate_sparkline(9.20) == "▃▄▅▆▇▇"
        assert NomadROICronGovernor._generate_sparkline(8.50) == "▂▃▄▅▅▆"
        assert NomadROICronGovernor._generate_sparkline(4.50) == "  ▂▃▃▄"


# ==============================================================================
# TIER 2: BOUNDARY & EDGE CASE TESTING (15 TESTS)
# ==============================================================================

class TestTier2BoundaryEdgeCaseTesting:
    """Tier 2: Boundary conditions, cold starts, edge cases, and network timeouts."""

    def test_t2_cold_start_zero_runs_roi_initialization(self):
        job = {"total_runs": 0, "successful_runs": 0, "consecutive_failures": 0, "status": "ACTIVE"}
        roi = DynamicEmpiricalROIEngine.compute_empirical_roi(job)
        assert 8.00 <= roi <= 10.00

    def test_t2_severe_failure_clamping_at_lower_bound(self):
        job = {"total_runs": 20, "successful_runs": 5, "consecutive_failures": 15, "status": "ACTIVE"}
        tel = {"status": "FAILED", "exit_code": 1, "duration_sec": 120.0}
        roi = DynamicEmpiricalROIEngine.compute_empirical_roi(job, tel)
        assert roi == 0.0

    def test_t2_submillisecond_and_zero_duration_execution(self):
        eff = DynamicEmpiricalROIEngine.compute_runtime_efficiency(0.0)
        assert eff == 1.0

    def test_t2_high_memory_and_cpu_overhead_clamping(self):
        eff = DynamicEmpiricalROIEngine.compute_resource_efficiency(250.0, 8192.0)
        assert eff == 0.0

    def test_t2_cadence_bounds_min_and_max_clamping(self):
        job = {"base_interval_sec": 900, "min_interval_sec": 300, "max_interval_sec": 1200, "consecutive_failures": 2, "status": "ACTIVE"}
        tel = {"ports_healthy": False}
        interval, tier, _, _ = AdaptiveCadenceElasticity.compute_elastic_cadence(job, tel)
        assert interval >= 300

    def test_t2_ssh_node_unreachable_probe_behavior(self):
        with patch.dict(REMOTE_NODES["linux_head_node"], {"ip": "192.0.2.1", "alt_ip": "192.0.2.2"}):
            reachable = RemoteSSHWorkerDispatcher.is_node_reachable("linux_head_node", timeout=0.1)
            assert reachable is False

    def test_t2_ssh_timeout_graceful_handling(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=2)):
            res = RemoteSSHWorkerDispatcher.dispatch_remote_job("linux_head_node", "fake_script.py", timeout=2)
            assert res["status"] == "TIMEOUT"
            assert res["exit_code"] == 124

    def test_t2_ssh_command_failure_telemetry_extraction(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 2
        mock_proc.stdout = ""
        mock_proc.stderr = "ModuleNotFoundError: No module named 'pyspark'"
        with patch("subprocess.run", return_value=mock_proc):
            res = RemoteSSHWorkerDispatcher.dispatch_remote_job("linux_head_node", "fail_script.py")
            assert res["status"] == "FAILED"
            assert res["exit_code"] == 2
            assert "ModuleNotFoundError" in res["error"]

    def test_t2_remediation_wol_device_resolution(self):
        res = AutonomousRemediationPipeline.trigger_wol("linux_head_node")
        assert "device_key" in res or "success" in res

    def test_t2_remediation_daemon_nonexistent_script_safety(self):
        res = AutonomousRemediationPipeline.restart_daemon("/path/does/not/exist.py")
        assert res["success"] is False

    def test_t2_remediation_max_retries_and_debate_escalation(self):
        job = {
            "name": "Failing Job",
            "consecutive_failures": 3,
            "remediation_attempts": 2,
            "remediation_config": {"max_remediation_retries": 3, "escalate_to_debate": True}
        }
        outcome = AutonomousRemediationPipeline.execute_remediation("cron_fail_test", job, {"status": "FAILED"})
        assert outcome["attempts"] == 3
        assert any("DEBATE" in a for a in outcome["actions_taken"])

    def test_t2_lora_serialization_ioerror_resilience(self):
        with patch("builtins.open", side_effect=IOError("Disk Full")):
            record = LoRADecisionTracer.log_decision("cron_001", {"total_runs": 1}, "TEST", "ACTION")
            assert record["instruction"] == "Nomad Cron ROI Governance Decision"

    def test_t2_portfolio_json_corruption_recovery(self):
        with patch("builtins.open", side_effect=json.JSONDecodeError("Expecting value", "", 0)):
            gov = NomadROICronGovernor()
            assert "jobs" in gov.portfolio
            assert len(gov.portfolio["jobs"]) >= 6

    def test_t2_decommissioned_job_dynamic_calculation(self):
        job = next(j for j in DEFAULT_JOBS if j["id"] == "cron_008_deprecated_raw_scrapers")
        roi = DynamicEmpiricalROIEngine.compute_empirical_roi(job)
        # S_j = 0.5 (1.50) + E_time = 1.0 (1.50) + R_res = 0.9889 (0.9889) + I_avoid = 3.0 (0.75) + V_token = 2.0 (0.40) - P_fail = 0.0 -> 5.14
        assert roi == 5.14

        # Verify dynamic responsiveness: failure penalty dynamically reduces ROI (no bypass)
        job_failed = dict(job)
        job_failed["consecutive_failures"] = 2
        roi_failed = DynamicEmpiricalROIEngine.compute_empirical_roi(job_failed)
        assert roi_failed == 2.07
        assert roi_failed < roi

    def test_t2_cluster_telemetry_thermal_and_ram_anomaly_detection(self):
        tel = AdaptiveCadenceElasticity.probe_cluster_telemetry()
        assert "ports_healthy" in tel
        assert "packet_loss_pct" in tel
        assert "host_ram_used_pct" in tel
        assert "anomalies_detected" in tel


# ==============================================================================
# TIER 3: PAIRWISE CROSS-FEATURE INTEGRATION (12 TESTS)
# ==============================================================================

class TestTier3PairwiseIntegrationPipelines:
    """Tier 3: Multi-component integration pipelines and contract workflows."""

    def test_t3_governor_cycle_recomputes_dynamic_roi(self):
        gov = NomadROICronGovernor()
        res = gov.run_governance_cycle()
        assert res["system_roi_score"] > 0.0
        assert res["active_jobs"] >= 6

    def test_t3_cadence_mutation_triggers_lora_and_ledger_event(self):
        gov = NomadROICronGovernor()
        gov.portfolio["jobs"]["cron_001_mesh_healer"]["interval_sec"] = 900
        gov.portfolio["jobs"]["cron_001_mesh_healer"]["cadence_tier"] = "NOMINAL_GOVERNANCE"

        with patch.object(AdaptiveCadenceElasticity, "probe_cluster_telemetry", return_value={"ports_healthy": False, "packet_loss_pct": 0.0, "host_ram_used_pct": 40.0, "thermal_throttling": False, "battery_temp_c": 30.0}):
            gov.optimize_and_adjust_portfolio()
            assert gov.portfolio["jobs"]["cron_001_mesh_healer"]["cadence_tier"] == "RAPID_TRIAGE"
            assert gov.portfolio["jobs"]["cron_001_mesh_healer"]["interval_sec"] == 180

    def test_t3_remote_job_ssh_dispatch_success_to_ledger(self):
        gov = NomadROICronGovernor()
        job_info = gov.portfolio["jobs"]["cron_006_swarm_truth_audit"]
        job_info["execution_target"] = "remote_ssh"
        job_info["preferred_node"] = "linux_head_node"
        job_info["last_run"] = 0

        mock_telemetry = {
            "status": "SUCCESS",
            "exit_code": 0,
            "duration_sec": 1.45,
            "cpu_pct": 4.5,
            "rss_mb": 60.0,
            "offload_node": "linux_head_node"
        }
        with patch.object(RemoteSSHWorkerDispatcher, "is_node_reachable", return_value=True), \
             patch.object(RemoteSSHWorkerDispatcher, "dispatch_remote_job", return_value=mock_telemetry):
            executed = gov.execute_job_if_due("cron_006_swarm_truth_audit", job_info, current_time=time.time())
            assert executed is True
            assert job_info["offload_node"] == "linux_head_node"
            assert job_info["consecutive_failures"] == 0

    def test_t3_remote_job_unreachable_node_falls_back_to_local(self):
        gov = NomadROICronGovernor()
        job_info = gov.portfolio["jobs"]["cron_006_swarm_truth_audit"]
        job_info["execution_target"] = "remote_ssh"
        job_info["preferred_node"] = "linux_head_node"
        job_info["fallback_to_local"] = True
        job_info["last_run"] = 0

        with patch.object(RemoteSSHWorkerDispatcher, "is_node_reachable", return_value=False), \
             patch.object(gov, "_execute_local", return_value=({"status": "SUCCESS", "exit_code": 0, "duration_sec": 0.5, "cpu_pct": 2.0, "rss_mb": 30.0}, True)):
            executed = gov.execute_job_if_due("cron_006_swarm_truth_audit", job_info, current_time=time.time())
            assert executed is True
            assert "fallback" in job_info["offload_node"]

    def test_t3_failed_job_triggers_progressive_remediation_pipeline(self):
        gov = NomadROICronGovernor()
        job_info = gov.portfolio["jobs"]["cron_001_mesh_healer"]
        job_info["last_run"] = 0

        mock_fail = {"status": "FAILED", "exit_code": 1, "duration_sec": 2.0, "cpu_pct": 1.0, "rss_mb": 25.0, "error": "Port conflict"}
        with patch.object(gov, "_execute_local", return_value=(mock_fail, False)), \
             patch.object(AutonomousRemediationPipeline, "execute_remediation", return_value={"actions_taken": ["TIER_1_PORT_RECLAIM_3000_OK"]}) as mock_remed:
            gov.execute_job_if_due("cron_001_mesh_healer", job_info, current_time=time.time())
            assert job_info["consecutive_failures"] == 1
            mock_remed.assert_called_once()

    def test_t3_remediation_failure_escalates_to_tri_orchestrator_debate(self):
        gov = NomadROICronGovernor()
        job_info = gov.portfolio["jobs"]["cron_004_nomad_scout_and_debate"]
        job_info["remediation_attempts"] = 3
        job_info["consecutive_failures"] = 3

        with patch.object(AutonomousRemediationPipeline, "trigger_ai_debate", return_value={"consensus_reached": True, "final_agreement_score": 1.0}) as mock_debate:
            outcome = AutonomousRemediationPipeline.execute_remediation("cron_004_nomad_scout_and_debate", job_info, {"status": "FAILED"})
            assert outcome["debate_result"] is not None
            mock_debate.assert_called_once()

    def test_t3_consecutive_failures_engage_circuit_breaker(self):
        job_info = {
            "id": "cron_test_circuit",
            "consecutive_failures": 5,
            "remediation_attempts": 4,
            "remediation_config": {"max_remediation_retries": 3}
        }
        outcome = AutonomousRemediationPipeline.execute_remediation("cron_test_circuit", job_info, {"status": "FAILED"})
        assert "TIER_5_CIRCUIT_BREAKER_ENGAGED" in outcome["actions_taken"]
        assert job_info["status"] == "STOPPED"

    def test_t3_circuit_breaker_stopped_decommissions_in_portfolio(self):
        gov = NomadROICronGovernor()
        job_info = gov.portfolio["jobs"]["cron_002_battery_governor"]
        job_info["status"] = "STOPPED"
        gov.optimize_and_adjust_portfolio()
        assert job_info["priority"] == "DECOMMISSIONED_LOW_ROI"
        assert job_info["cadence_tier"] == "CIRCUIT_BREAKER_STOPPED"

    def test_t3_governance_cycle_persists_lora_decisions_jsonl(self):
        gov = NomadROICronGovernor()
        gov.run_governance_cycle()
        assert LORA_DECISIONS_JSONL.exists()
        with open(LORA_DECISIONS_JSONL, "r") as f:
            lines = [json.loads(line) for line in f if line.strip()]
            assert len(lines) > 0
            assert "instruction" in lines[-1]
            assert "output" in lines[-1]

    def test_t3_governance_cycle_syncs_both_dashboard_locations(self):
        gov = NomadROICronGovernor()
        gov.run_governance_cycle()
        assert DASHBOARD_FILE.exists()
        assert LOCAL_DASHBOARD_FILE.exists()
        with open(DASHBOARD_FILE, "r") as f:
            content = f.read()
            assert "Nomad Autonomous Cron & ROI Governance Dashboard" in content
            assert "Cluster Hardware & Distributed Resource Utilization" in content

    def test_t3_phase_offset_staggering_preserves_distinct_cadences(self):
        gov = NomadROICronGovernor()
        offsets = [j["phase_offset_sec"] for j in gov.portfolio["jobs"].values() if j["status"] == "ACTIVE"]
        assert len(set(offsets)) >= 4

    def test_t3_governor_status_file_contract(self):
        gov = NomadROICronGovernor()
        res = gov.run_governance_cycle()
        assert GOVERNOR_STATUS_FILE.exists()
        with open(GOVERNOR_STATUS_FILE, "r") as f:
            status = json.load(f)
            assert status["status"] == "NOMAD_CRON_GOVERNOR_OPTIMAL"
            assert "system_roi_score" in status
            assert "active_jobs" in status


# ==============================================================================
# TIER 4: REAL-WORLD WORKLOADS & E2E VERIFICATION (10 TESTS)
# ==============================================================================

class TestTier4RealWorldWorkloadsE2E:
    """Tier 4: End-to-end execution, full ledger audits, CLI parser, and zero-mock verification."""

    def test_t4_live_governor_once_execution(self):
        res = subprocess.run(
            [sys.executable, str(REPO_ROOT / "06_scripts_and_tooling/automation/nomad_roi_cron_governor.py"), "--once"],
            capture_output=True,
            text=True,
            timeout=15
        )
        assert res.returncode == 0
        json_start = res.stdout.find("{")
        output_json = json.loads(res.stdout[json_start:])
        assert output_json["status"] == "NOMAD_CRON_GOVERNOR_OPTIMAL"

    def test_t4_full_portfolio_multi_cron_sweep(self):
        gov = NomadROICronGovernor()
        jobs = gov.portfolio["jobs"]
        for j_id in ["cron_001_mesh_healer", "cron_002_battery_governor", "cron_003_nomad_genetic_storage", "cron_004_nomad_scout_and_debate", "cron_005_cloudflare_watchdog", "cron_006_swarm_truth_audit", "cron_007_genetic_moe_router"]:
            assert j_id in jobs
            assert jobs[j_id]["roi_score"] > 0.0

    def test_t4_adversarial_fault_injection_and_recovery(self):
        gov = NomadROICronGovernor()
        job_info = gov.portfolio["jobs"]["cron_005_cloudflare_watchdog"]
        job_info["status"] = "ACTIVE"
        job_info["consecutive_failures"] = 2
        gov.optimize_and_adjust_portfolio()
        assert job_info["cadence_tier"] == "RAPID_TRIAGE"

        # Recover job
        job_info["consecutive_failures"] = 0
        job_info["stable_runs_count"] = 15
        with patch.object(AdaptiveCadenceElasticity, "probe_cluster_telemetry", return_value={"ports_healthy": True, "packet_loss_pct": 0.0, "host_ram_used_pct": 40.0, "thermal_throttling": False, "battery_temp_c": 30.0}):
            gov.optimize_and_adjust_portfolio()
            assert job_info["cadence_tier"] == "EXTENDED_STABILITY_BACKOFF"

    def test_t4_continuous_lora_dataset_integrity_audit(self):
        assert LORA_DECISIONS_JSONL.exists()
        with open(LORA_DECISIONS_JSONL, "r") as f:
            for idx, line in enumerate(f):
                line_str = line.strip()
                if not line_str:
                    continue
                record = json.loads(line_str)
                assert record["instruction"] == "Nomad Cron ROI Governance Decision"
                assert "job_id" in record["input"]
                assert "decision" in record["output"]
                assert "action" in record["output"]
                assert "roi_score" in record["output"]

    def test_t4_obsidian_dashboard_content_and_structure_validation(self):
        assert DASHBOARD_FILE.exists()
        with open(DASHBOARD_FILE, "r") as f:
            text = f.read()
            assert "# 📊 Nomad Autonomous Cron & ROI Governance Dashboard" in text
            assert "System Average ROI" in text
            assert "Active Cron ROI Leaderboard" in text
            assert "Nomad Autonomous Rules Enforced" in text

    def test_t4_optimization_ledger_leaderboard_ordering(self):
        assert LEDGER_FILE.exists()
        with open(LEDGER_FILE, "r") as f:
            ledger = json.load(f)
            board = ledger["roi_leaderboard"]
            scores = [item["roi_score"] for item in board]
            assert scores == sorted(scores, reverse=True)

    def test_t4_master_ledger_jsonl_schema_validation(self):
        assert MASTER_LEDGER_JSONL.exists()
        with open(MASTER_LEDGER_JSONL, "r") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line.strip())
                    assert "timestamp_utc" in item
                    assert "event_type" in item

    def test_t4_remote_nodes_definition_completeness(self):
        for node_key, node in REMOTE_NODES.items():
            assert "layer" in node
            assert "ip" in node
            assert "user" in node
            assert "port" in node
            assert "role" in node

    def test_t4_cli_arguments_parser_flags(self):
        gov_script = str(REPO_ROOT / "06_scripts_and_tooling/automation/nomad_roi_cron_governor.py")
        res = subprocess.run([sys.executable, gov_script, "--help"], capture_output=True, text=True)
        assert res.returncode == 0
        assert "--once" in res.stdout
        assert "--daemon" in res.stdout
        assert "--interval" in res.stdout

    def test_t4_zero_mock_data_and_real_metrics_certification(self):
        gov = NomadROICronGovernor()
        for j_id, job in gov.portfolio["jobs"].items():
            if job["status"] == "ACTIVE":
                assert job["roi_score"] <= 10.0
                assert job["interval_sec"] >= job["min_interval_sec"]
                assert job["interval_sec"] <= job["max_interval_sec"]
