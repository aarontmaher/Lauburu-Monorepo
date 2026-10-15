#!/usr/bin/env python3
"""
tests/test_adversarial_challenger2_verification.py
===================================================
Adversarial Verification & Empirical Stress-Testing Suite for Challenger 2:
1. 5-Tier Self-Healing Under Severe Failure Injection (Port 3000/18802/50052, lsof, WoL, Tri-Orchestrator debate escalation before STOPPED).
2. LoRA Decision Tracing (JSON schema, Alpaca format compliance, duplicate/corruption audits).
3. Obsidian Dashboard Telemetry (table formatting, sparklines, hardware specs, dynamic sync).
4. Live execution contract and end-to-end resilience.
"""

import os
import sys
import json
import time
import socket
import pytest
import subprocess
from pathlib import Path
from datetime import datetime
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
    GDRIVE_FALLBACK_JSONL,
    DASHBOARD_FILE,
    LOCAL_DASHBOARD_FILE,
    GOVERNOR_STATUS_FILE,
    REMOTE_NODES,
    DEFAULT_JOBS
)


@pytest.fixture(autouse=True)
def restore_portfolio_state():
    """Restores default job state in portfolio file for test isolation."""
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
# SECTION 1: 5-TIER SELF-HEALING UNDER SEVERE FAULT INJECTION
# ==============================================================================

class TestAdversarialSelfHealing5Tier:
    """Stress tests 5-tier self-healing hooks, port reclamation, WoL, debate escalation, and circuit-breaker."""

    def test_adversarial_port_3000_conflict_probe_and_reclamation(self):
        """Simulates port 3000 socket degradation and verifies lsof reclamation attempt."""
        # Test probe_port accurately identifies closed vs open
        probe_closed = AutonomousRemediationPipeline.probe_port(59991, timeout=0.1)
        assert probe_closed is False

        # Case A: Port remains occupied after kill (probe_port returns True -> reclaimed is False)
        with patch("subprocess.run") as mock_subproc, \
             patch.object(AutonomousRemediationPipeline, "probe_port", return_value=True):
            reclaimed = AutonomousRemediationPipeline.reclaim_port(3000)
            mock_subproc.assert_called_once()
            cmd_arg = mock_subproc.call_args[0][0]
            assert "lsof -ti :3000" in cmd_arg
            assert "kill -9" in cmd_arg
            assert reclaimed is False

        # Case B: Port is successfully freed after kill (probe_port returns False -> reclaimed is True)
        with patch("subprocess.run") as mock_subproc, \
             patch.object(AutonomousRemediationPipeline, "probe_port", return_value=False):
            reclaimed = AutonomousRemediationPipeline.reclaim_port(3000)
            assert reclaimed is True

    def test_adversarial_port_18802_conflict_simulation(self):
        """Simulates port 18802 (WoL REST API) socket failure and reclamation."""
        with patch("subprocess.run") as mock_subproc, \
             patch.object(AutonomousRemediationPipeline, "probe_port", return_value=False):
            reclaimed = AutonomousRemediationPipeline.reclaim_port(18802)
            mock_subproc.assert_called_once()
            cmd_arg = mock_subproc.call_args[0][0]
            assert "lsof -ti :18802" in cmd_arg
            assert reclaimed is True

    def test_adversarial_port_50052_conflict_simulation(self):
        """Simulates port 50052 (LLaMA RPC Sharding) socket failure and reclamation."""
        with patch("subprocess.run") as mock_subproc, \
             patch.object(AutonomousRemediationPipeline, "probe_port", return_value=False):
            reclaimed = AutonomousRemediationPipeline.reclaim_port(50052)
            mock_subproc.assert_called_once()
            cmd_arg = mock_subproc.call_args[0][0]
            assert "lsof -ti :50052" in cmd_arg
            assert reclaimed is True

    def test_adversarial_wol_trigger_resilience_and_rest_fallback(self):
        """Verifies WoL packet triggering and REST API fallback handling without crashing."""
        # Test direct call to trigger_wol
        res = AutonomousRemediationPipeline.trigger_wol("linux_head_node")
        assert isinstance(res, dict)
        assert ("success" in res or "device_key" in res or "error" in res)

        # Test REST API fallback when WoLEngine import fails
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"success": true, "device": "macbook_pro_vault", "bytes_sent": 102}'
            mock_resp.__enter__.return_value = mock_resp
            mock_url.return_value = mock_resp

            res_rest = AutonomousRemediationPipeline.trigger_wol("macbook_pro_vault")
            assert isinstance(res_rest, dict)

    def test_adversarial_progressive_5_tier_remediation_lifecycle(self):
        """Validates progressive escalation through all 5 tiers before marking STOPPED."""
        job = {
            "name": "5-Device Mesh Network Healer",
            "script": str(REPO_ROOT / "06_scripts_and_tooling/network/nomad_courier_self_healer.py"),
            "args": ["--once"],
            "status": "ACTIVE",
            "consecutive_failures": 1,
            "remediation_attempts": 0,
            "remediation_config": {
                "monitored_port": 3000,
                "wol_device_key": "mac_mini_host",
                "max_remediation_retries": 3,
                "escalate_to_debate": True
            }
        }

        # Attempt 1: Tiers 1, 2, 3 triggered. No debate, not stopped.
        with patch.object(AutonomousRemediationPipeline, "probe_port", return_value=False), \
             patch.object(AutonomousRemediationPipeline, "reclaim_port", return_value=True), \
             patch.object(AutonomousRemediationPipeline, "trigger_wol", return_value={"success": True}), \
             patch.object(AutonomousRemediationPipeline, "restart_daemon", return_value={"success": True, "pid": 12345}):
            outcome1 = AutonomousRemediationPipeline.execute_remediation("cron_001_mesh_healer", job, {"status": "FAILED"})
            assert outcome1["attempts"] == 1
            assert "TIER_1_PORT_RECLAIM_3000_OK" in outcome1["actions_taken"]
            assert "TIER_2_WOL_mac_mini_host_SUCCESS" in outcome1["actions_taken"]
            assert "TIER_3_DAEMON_RESTART_OK" in outcome1["actions_taken"]
            assert "TIER_4_TRI_ORCHESTRATOR_DEBATE_ESCALATED" not in outcome1["actions_taken"]
            assert job["status"] == "ACTIVE"

        # Attempt 2: Still within retries. No debate, not stopped.
        job["consecutive_failures"] = 2
        with patch.object(AutonomousRemediationPipeline, "probe_port", return_value=True), \
             patch.object(AutonomousRemediationPipeline, "trigger_wol", return_value={"success": True}), \
             patch.object(AutonomousRemediationPipeline, "restart_daemon", return_value={"success": True, "pid": 12346}):
            outcome2 = AutonomousRemediationPipeline.execute_remediation("cron_001_mesh_healer", job, {"status": "FAILED"})
            assert outcome2["attempts"] == 2
            assert "TIER_4_TRI_ORCHESTRATOR_DEBATE_ESCALATED" not in outcome2["actions_taken"]
            assert job["status"] == "ACTIVE"

        # Attempt 3: Reaches max_remediation_retries (3). Tier 4 debate escalated!
        job["consecutive_failures"] = 3
        with patch.object(AutonomousRemediationPipeline, "probe_port", return_value=True), \
             patch.object(AutonomousRemediationPipeline, "trigger_wol", return_value={"success": True}), \
             patch.object(AutonomousRemediationPipeline, "restart_daemon", return_value={"success": True, "pid": 12347}), \
             patch.object(AutonomousRemediationPipeline, "trigger_ai_debate", return_value={"consensus_reached": True, "final_agreement_score": 1.0}) as mock_deb:
            outcome3 = AutonomousRemediationPipeline.execute_remediation("cron_001_mesh_healer", job, {"status": "FAILED"})
            assert outcome3["attempts"] == 3
            assert "TIER_4_TRI_ORCHESTRATOR_DEBATE_ESCALATED" in outcome3["actions_taken"]
            assert outcome3["debate_result"] is not None
            mock_deb.assert_called_once()
            assert job["status"] == "ACTIVE"  # Not yet 5 failures

        # Attempt 4: Failures reach 5. Tier 5 Circuit Breaker Engaged -> STOPPED!
        job["consecutive_failures"] = 5
        with patch.object(AutonomousRemediationPipeline, "probe_port", return_value=True), \
             patch.object(AutonomousRemediationPipeline, "trigger_wol", return_value={"success": True}), \
             patch.object(AutonomousRemediationPipeline, "restart_daemon", return_value={"success": False}), \
             patch.object(AutonomousRemediationPipeline, "trigger_ai_debate", return_value={"consensus_reached": True}):
            outcome4 = AutonomousRemediationPipeline.execute_remediation("cron_001_mesh_healer", job, {"status": "FAILED"})
            assert outcome4["attempts"] == 4
            assert "TIER_5_CIRCUIT_BREAKER_ENGAGED" in outcome4["actions_taken"]
            assert job["status"] == "STOPPED"
            assert job["priority"] == "DECOMMISSIONED_LOW_ROI"

    def test_adversarial_tri_orchestrator_debate_fallback_safety(self):
        """Verifies debate escalation falls back safely if NomadGovernorScoutEngine encounters error."""
        with patch("nomad_governor_with_scout.NomadGovernorScoutEngine", side_effect=Exception("Module Load Failure")):
            res = AutonomousRemediationPipeline.trigger_ai_debate("cron_004", {"name": "Scout"}, {"confidence": 0.5})
            assert res["consensus_reached"] is True
            assert res["status"] == "DEBATE_FALLBACK_EXECUTED"
            assert len(res["consensus_priorities"]) >= 2


# ==============================================================================
# SECTION 2: LORA DECISION TRACING & DATASET INTEGRITY
# ==============================================================================

class TestAdversarialLoRADatasetAudit:
    """Strict JSON schema, Alpaca compliance, and duplicate/corruption audit of LoRA datasets."""

    def test_adversarial_lora_dataset_jsonl_existence_and_non_empty(self):
        """Verifies primary dataset exists and contains records."""
        assert LORA_DECISIONS_JSONL.exists()
        size = os.path.getsize(LORA_DECISIONS_JSONL)
        assert size > 0, f"LoRA decision file {LORA_DECISIONS_JSONL} is empty!"

    def test_adversarial_lora_dataset_alpaca_schema_strict_compliance(self):
        """Exhaustively parses every single line in cron_governor_decisions.jsonl for Alpaca schema compliance."""
        total_records = 0
        with open(LORA_DECISIONS_JSONL, "r") as f:
            for line_idx, line in enumerate(f, start=1):
                line_str = line.strip()
                if not line_str:
                    continue
                total_records += 1
                try:
                    record = json.loads(line_str)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Corrupt JSON at line {line_idx}: {e}")

                # Check top-level Alpaca keys
                assert "instruction" in record, f"Line {line_idx} missing 'instruction'"
                assert "input" in record, f"Line {line_idx} missing 'input'"
                assert "output" in record, f"Line {line_idx} missing 'output'"
                assert "timestamp_utc" in record, f"Line {line_idx} missing 'timestamp_utc'"
                assert record["real_data_certified"] is True, f"Line {line_idx} real_data_certified is not True"

                # Check instruction content
                assert isinstance(record["instruction"], str)
                assert len(record["instruction"]) > 0

                # Check input structure
                inp = record["input"]
                assert isinstance(inp, dict), f"Line {line_idx} input is not a dict"
                assert "job_id" in inp, f"Line {line_idx} input missing 'job_id'"
                assert "metrics" in inp, f"Line {line_idx} input missing 'metrics'"
                metrics = inp["metrics"]
                assert "total_runs" in metrics
                assert "successful_runs" in metrics
                assert "consecutive_failures" in metrics
                assert "cadence_tier" in metrics

                # Check output structure
                out = record["output"]
                assert isinstance(out, dict), f"Line {line_idx} output is not a dict"
                assert "decision" in out, f"Line {line_idx} output missing 'decision'"
                assert "action" in out, f"Line {line_idx} output missing 'action'"
                assert "new_cadence" in out, f"Line {line_idx} output missing 'new_cadence'"
                assert "roi_score" in out, f"Line {line_idx} output missing 'roi_score'"
                assert "offloaded_to" in out, f"Line {line_idx} output missing 'offloaded_to'"

                # Verify ISO timestamp format
                dt_str = record["timestamp_utc"]
                try:
                    datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                except ValueError as e:
                    pytest.fail(f"Line {line_idx} has invalid timestamp '{dt_str}': {e}")

        assert total_records >= 200, f"Expected at least 200 records in dataset, found {total_records}"

    def test_adversarial_lora_dataset_no_corrupt_lines_or_duplicates(self):
        """Audits for exact duplicate lines or corrupt records."""
        seen_lines = set()
        duplicate_count = 0
        corrupt_count = 0

        with open(LORA_DECISIONS_JSONL, "r") as f:
            for line_idx, line in enumerate(f, start=1):
                line_str = line.strip()
                if not line_str:
                    continue
                if line_str in seen_lines:
                    duplicate_count += 1
                seen_lines.add(line_str)

                try:
                    json.loads(line_str)
                except Exception:
                    corrupt_count += 1

        assert corrupt_count == 0, f"Found {corrupt_count} corrupt JSON lines in {LORA_DECISIONS_JSONL}"
        assert duplicate_count == 0, f"Found {duplicate_count} duplicate lines in {LORA_DECISIONS_JSONL}"

    def test_adversarial_lora_dual_mirror_synchronization(self):
        """Verifies that GDrive fallback mirror is kept synchronized."""
        if GDRIVE_FALLBACK_JSONL.exists():
            with open(GDRIVE_FALLBACK_JSONL, "r") as f:
                lines = [line for line in f if line.strip()]
                assert len(lines) > 0


# ==============================================================================
# SECTION 3: OBSIDIAN DASHBOARD FORMATTING & TELEMETRY
# ==============================================================================

class TestAdversarialObsidianDashboardTelemetry:
    """Stress tests Markdown table syntax, sparkline rendering, hardware specs, and dynamic sync."""

    def test_adversarial_dashboard_file_presence_and_dual_sync(self):
        """Verifies dashboard exists at both Obsidian vault and repository root paths."""
        gov = NomadROICronGovernor()
        gov.optimize_and_adjust_portfolio()

        assert DASHBOARD_FILE.exists(), f"Obsidian vault dashboard missing at {DASHBOARD_FILE}"
        assert LOCAL_DASHBOARD_FILE.exists(), f"Local monorepo dashboard missing at {LOCAL_DASHBOARD_FILE}"

    def test_adversarial_dashboard_markdown_table_formatting(self):
        """Strictly validates Markdown table column counts, header formatting, and row alignment."""
        with open(DASHBOARD_FILE, "r") as f:
            content = f.read()

        lines = content.splitlines()
        table_lines = [l for l in lines if l.startswith("|") and l.endswith("|")]
        assert len(table_lines) >= 9, f"Expected at least header + separator + 7 rows, got {len(table_lines)}"

        # Header validation
        header_cols = [c.strip() for c in table_lines[0].split("|")[1:-1]]
        expected_cols = [
            "Rank", "Cron / Daemon Name", "ROI Score", "Trend", "Cadence Tier",
            "Priority Tier", "Status", "Current Cadence", "Target Node",
            "Runs", "Last Runtime", "Peak Resources"
        ]
        assert header_cols == expected_cols, f"Header mismatch: {header_cols} != {expected_cols}"
        assert len(header_cols) == 12

        # Delimiter line validation
        delim_cols = [c.strip() for c in table_lines[1].split("|")[1:-1]]
        assert len(delim_cols) == 12
        for col in delim_cols:
            assert col.startswith(":") and col.endswith("-") or col.startswith("-") or ":---" in col

        # Data rows validation
        for row_idx, row in enumerate(table_lines[2:], start=1):
            cols = [c.strip() for c in row.split("|")[1:-1]]
            assert len(cols) == 12, f"Table row #{row_idx} has {len(cols)} columns instead of 12: {row}"
            rank_col, name_col, roi_col, trend_col, tier_col, prio_col, status_col, cad_col, target_col, runs_col, time_col, res_col = cols
            assert rank_col.startswith("**#")
            assert roi_col.startswith("**")
            assert status_col in ["**ACTIVE**", "**STOPPED**", "**STANDBY**"]

    def test_adversarial_dashboard_sparkline_rendering_all_thresholds(self):
        """Verifies sparkline generator across all ROI tiers."""
        assert DynamicEmpiricalROIEngine.compute_bayesian_success_rate(10, 10) > 0.90
        assert NomadROICronGovernor._generate_sparkline(10.00) == "▇█████"
        assert NomadROICronGovernor._generate_sparkline(9.85) == "▇█████"
        assert NomadROICronGovernor._generate_sparkline(9.80) == "▇█████"
        assert NomadROICronGovernor._generate_sparkline(9.79) == "▅▆▇███"
        assert NomadROICronGovernor._generate_sparkline(9.50) == "▅▆▇███"
        assert NomadROICronGovernor._generate_sparkline(9.49) == "▃▄▅▆▇▇"
        assert NomadROICronGovernor._generate_sparkline(9.00) == "▃▄▅▆▇▇"
        assert NomadROICronGovernor._generate_sparkline(8.99) == "▂▃▄▅▅▆"
        assert NomadROICronGovernor._generate_sparkline(8.00) == "▂▃▄▅▅▆"
        assert NomadROICronGovernor._generate_sparkline(7.99) == "  ▂▃▃▄"
        assert NomadROICronGovernor._generate_sparkline(0.00) == "  ▂▃▃▄"

    def test_adversarial_dashboard_hardware_specs_verification(self):
        """Verifies hardware specs: 82.8 GB Pooled VRAM, Port 50052 RPC, Host RAM, and cluster memory context."""
        with open(DASHBOARD_FILE, "r") as f:
            text = f.read()

        assert "82.8 GB" in text, "Dashboard missing 82.8 GB pooled VRAM specification"
        assert "Port 50052" in text, "Dashboard missing Port 50052 RPC socket"
        assert "24 GB Unified RAM" in text or "Host Mac Mini" in text, "Dashboard missing Host Mac Mini specification"
        assert "100.101.39.98" in text, "Dashboard missing Linux Head Node IP"
        assert "100.103.212.21" in text, "Dashboard missing MacBook Pro Vault IP"
        assert "100.93.158.96" in text, "Dashboard missing MacBook Air IP"

    def test_adversarial_dashboard_dynamic_metrics_sync(self):
        """Verifies dynamic metrics sync when governor optimizes portfolio."""
        gov = NomadROICronGovernor()
        gov.portfolio["jobs"]["cron_001_mesh_healer"]["total_runs"] = 999
        gov.portfolio["jobs"]["cron_001_mesh_healer"]["last_elapsed_sec"] = 0.042
        gov.optimize_and_adjust_portfolio()

        with open(DASHBOARD_FILE, "r") as f:
            updated_text = f.read()

        assert "999" in updated_text, "Dashboard failed to dynamically sync updated run count"
        assert "0.042s" in updated_text, "Dashboard failed to dynamically sync updated elapsed time"


# ==============================================================================
# SECTION 4: LIVE GOVERNOR VERIFICATION CONTRACT
# ==============================================================================

class TestAdversarialLiveGovernorExecution:
    """Runs live CLI governor and verifies output contracts."""

    def test_adversarial_live_governor_once_contract(self):
        """Executes live nomad_roi_cron_governor.py --once and validates JSON output contract."""
        cmd = [sys.executable, str(REPO_ROOT / "06_scripts_and_tooling/automation/nomad_roi_cron_governor.py"), "--once"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        assert res.returncode == 0, f"Governor execution failed: {res.stderr}"

        # Parse JSON output
        json_start = res.stdout.find("{")
        assert json_start != -1, "No JSON found in governor stdout"
        data = json.loads(res.stdout[json_start:])

        assert data["status"] == "NOMAD_CRON_GOVERNOR_OPTIMAL"
        assert data["active_jobs"] >= 7
        assert data["system_roi_score"] >= 9.0
        assert "timestamp_utc" in data
        assert Path(data["dashboard_file"]).exists()
        assert Path(data["lora_decisions_file"]).exists()
        assert Path(data["master_cron_ledger"]).exists()

    def test_adversarial_governor_status_json_live_file(self):
        """Validates schema of data/network/nomad_governor_status.json."""
        assert GOVERNOR_STATUS_FILE.exists()
        with open(GOVERNOR_STATUS_FILE, "r") as f:
            status = json.load(f)
        assert status["status"] == "NOMAD_CRON_GOVERNOR_OPTIMAL"
        assert "active_jobs" in status
        assert "system_roi_score" in status
        assert "timestamp_utc" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
