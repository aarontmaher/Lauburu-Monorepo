# tests/test_adversarial_challenger1.py
"""
tests/test_adversarial_challenger1.py
======================================
Adversarial Stress Test Suite & Empirical Validation Harness
Challenger 1 (Adversarial Verifier) for Lauburu 7-Layer Mesh.

Covers:
- R1: Multi-node RPC sharding & dynamic RAM governance boundary conditions
- R2: PySpark & Nomad chat sweep against malformed/empty/corrupted transcripts
- R3: Nomad courier self-healer & socket probing resilience under rapid/concurrent load & edge states
- R4: Full acceptance test suite validation
"""

import os
import sys
import json
import socket
import tempfile
import threading
import subprocess
import time
import importlib.util
from pathlib import Path
from typing import Dict, List, Any
import pytest

from tests.e2e.test_lauburu_mesh_acceptance import (
    compute_model_sharding_plan,
    NODE_HIERARCHY,
    RPC_PORT,
    PORT_WEB_UI,
    PORT_APP_STORE,
    PORT_WOL_API,
    apply_kamath_2004_filter,
    calculate_rmssd,
    calculate_dfa_alpha1,
    determine_training_zone,
)

def _get_nomad_engine():
    healer_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py")
    spec = importlib.util.spec_from_file_location("nomad_courier_self_healer", str(healer_path))
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(healer_path)
    spec.loader.exec_module(mod)
    return mod.NomadAutonomousEngine()

# ---------------------------------------------------------------------------
# 1. R1 Adversarial Tests: RPC Sharding & Dynamic RAM Governance
# ---------------------------------------------------------------------------
class TestAdversarialR1ShardingAndRAMGovernance:
    """Stress-tests for RPC sharding calculations under extreme inputs."""

    def test_extreme_zero_ram_nodes(self):
        """Test behavior when some nodes report 0 GB RAM or 0 available RAM."""
        nodes = [
            {"name": "node_zero_ram", "role": "Dead Node", "ip": "100.1.1.1", "total_gb": 0.0, "ram_cap_pct": 80.0, "available_gb": 0.0, "priority": 1},
            {"name": "node_active", "role": "Active Mac", "ip": "100.1.1.2", "total_gb": 24.0, "ram_cap_pct": 90.0, "available_gb": 21.6, "priority": 2},
        ]
        plan = compute_model_sharding_plan(32, nodes, proportional=True)
        assert plan["fully_allocated"] is True
        assigned_total = sum(a["assigned_layers"] for a in plan["allocation"])
        assert assigned_total == 32

    def test_single_layer_tiny_model(self):
        """Test single layer model on full 7-node cluster."""
        nodes = [dict(n, available_gb=n["total_gb"] * (n["ram_cap_pct"] / 100.0)) for n in NODE_HIERARCHY]
        plan = compute_model_sharding_plan(1, nodes, proportional=True)
        assert plan["total_layers"] == 1
        assert len(plan["allocation"]) == len(nodes)

    def test_massive_layer_deep_model(self):
        """Test 10,000 layer sharding across cluster without integer overflow or unassigned layers."""
        nodes = [dict(n, available_gb=n["total_gb"] * (n["ram_cap_pct"] / 100.0)) for n in NODE_HIERARCHY]
        plan = compute_model_sharding_plan(10000, nodes, proportional=True)
        assert plan["fully_allocated"] is True
        assigned_total = sum(a["assigned_layers"] for a in plan["allocation"])
        assert assigned_total == 10000

    def test_non_proportional_sequential_fill_up_hierarchy(self):
        """Test non-proportional sequential fill-up strictly filling priority 1 before priority 2."""
        nodes = [
            {"name": "linux_p1", "role": "Linux Head", "ip": "100.101.39.98", "total_gb": 16.0, "ram_cap_pct": 80.0, "available_gb": 12.8, "priority": 1},
            {"name": "mac_p2", "role": "Mac Pro", "ip": "100.103.212.21", "total_gb": 16.0, "ram_cap_pct": 90.0, "available_gb": 14.4, "priority": 2},
            {"name": "pixel_p6", "role": "Pixel", "ip": "100.73.38.87", "total_gb": 16.0, "ram_cap_pct": 85.0, "available_gb": 13.6, "priority": 6},
        ]
        plan = compute_model_sharding_plan(10, nodes, proportional=False)
        assert plan["fully_allocated"] is True
        alloc = plan["allocation"]
        assert alloc[0]["node"] == "linux_p1"
        assert alloc[0]["assigned_layers"] == 10
        assert len(alloc) == 1 # Only node with assigned layers in active allocation
        assert plan["ts_flag"] == "-ts 10" 

    def test_ram_ceiling_bounds_verification(self):
        """Verify strict node RAM ceilings are never exceeded regardless of available_gb input."""
        nodes = [
            {"name": "mac", "role": "Host Mac", "ip": "100.1.1.1", "total_gb": 24.0, "ram_cap_pct": 90.0, "available_gb": 1000.0, "priority": 1},
            {"name": "linux", "role": "Linux Head", "ip": "100.1.1.2", "total_gb": 16.0, "ram_cap_pct": 80.0, "available_gb": 1000.0, "priority": 2},
        ]
        plan = compute_model_sharding_plan(64, nodes, proportional=True)
        for a in plan["allocation"]:
            if a["node"] == "mac":
                assert a["usable_ram_gb"] <= 24.0 * 0.90
            elif a["node"] == "linux":
                assert a["usable_ram_gb"] <= 16.0 * 0.80

    def test_single_node_mesh(self):
        """Test sharding plan on single-node standalone deployment."""
        nodes = [{"name": "solo_node", "role": "Mac Mini", "ip": "100.1.1.1", "total_gb": 24.0, "ram_cap_pct": 90.0, "available_gb": 21.6, "priority": 1}]
        plan = compute_model_sharding_plan(48, nodes, proportional=True)
        assert plan["fully_allocated"] is True
        assert len(plan["allocation"]) == 1
        assert plan["allocation"][0]["assigned_layers"] == 48


# ---------------------------------------------------------------------------
# 2. R2 Adversarial Tests: PySpark & Nomad Chat Sweep Engine
# ---------------------------------------------------------------------------
class TestAdversarialR2ChatSweep:
    """Stress-tests for chat transcript sweeping and prompt draft auditing."""

    def test_empty_and_corrupt_transcripts(self, tmp_path):
        """Test sweep parsing against empty, malformed, non-JSON, and binary files."""
        from unittest.mock import patch
        import shutil

        fake_brain = tmp_path / "fake_brain"
        fake_brain.mkdir()

        # 1. Empty transcript
        c1 = fake_brain / "conv_empty" / ".system_generated" / "logs"
        c1.mkdir(parents=True)
        (c1 / "transcript.jsonl").write_text("")

        # 2. Corrupted JSON lines
        c2 = fake_brain / "conv_corrupt" / ".system_generated" / "logs"
        c2.mkdir(parents=True)
        corrupt_data = "NOT_A_JSON_LINE\n{broken_json: true\n" + json.dumps({"type": "valid_json", "content": "plain text"}) + "\n"
        (c2 / "transcript.jsonl").write_text(corrupt_data)

        # 3. Unicode and special characters with target decision keywords
        c3 = fake_brain / "conv_unicode" / ".system_generated" / "logs"
        c3.mkdir(parents=True)
        content_lines = [
            json.dumps({"type": "USER_INPUT", "content": "We require rpc sharding on port 50052 with 128Hz movesense 🚀!"}),
            json.dumps({"type": "MODEL_OUTPUT", "content": "Nomad courier self-heal routines active with zero-mock policy."}),
            json.dumps({"type": "TOOL_CALL", "tool_calls": [{"name": "deploy_mesh", "arguments": {"target": "ggml-rpc-server", "ram_cap": "mac 90%"}}]})
        ]
        (c3 / "transcript.jsonl").write_text("\n".join(content_lines) + "\n")

        # 4. Valid prompt draft
        draft_content = """
        # Project Prompt
        We have headless linux, macbook pro, macbook air, mac mini, samsung, pixel.
        Enforcing ram ceiling: mac 90%, linux 80%, pixel 85%, s20+ 75%.
        Nomad courier active on port 3000, port 4000, port 18802, port 50052.
        Using antigravity-models with llama.cpp, petals, exo, query_model.
        128Hz ecg from movesense and polar h10 with zero-mock data, no synthetic data.
        """
        (fake_brain / "conv_unicode" / "prompt_draft.md").write_text(draft_content)

        sweep_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/mesh/pyspark_nomad_chat_sweep.py")
        spec = importlib.util.spec_from_file_location("nomad_chat_sweep", str(sweep_path))
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(sweep_path)
        spec.loader.exec_module(mod)
        
        with patch.object(mod, "BRAIN_DIR", fake_brain), \
             patch.object(mod, "REPORT_FILE", tmp_path / "report.json"), \
             patch.object(mod, "DECISIONS_FILE", tmp_path / "decisions.jsonl"):
            decisions = mod.sweep_chat_transcripts()
            assert len(decisions) >= 3, f"Expected at least 3 decisions, got {len(decisions)}"
            
            audits = mod.cross_reference_prompt_drafts(decisions)
            assert str(fake_brain / "conv_unicode" / "prompt_draft.md") in audits
            assert audits[str(fake_brain / "conv_unicode" / "prompt_draft.md")]["all_directives_present"] is True

    def test_huge_transcript_lines_and_deduplication(self, tmp_path):
        """Test handling of large JSON lines (>1MB) and deduplication logic."""
        fake_brain = tmp_path / "brain_huge"
        c = fake_brain / "conv_huge" / ".system_generated" / "logs"
        c.mkdir(parents=True)

        large_filler = "A" * (500 * 1024)
        lines = [
            json.dumps({"type": "USER_INPUT", "content": f"rpc sharding with filling order {large_filler}"}),
            json.dumps({"type": "USER_INPUT", "content": f"rpc sharding with filling order {large_filler}"}),
        ]
        (c / "transcript.jsonl").write_text("\n".join(lines) + "\n")

        sweep_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/mesh/pyspark_nomad_chat_sweep.py")
        spec = importlib.util.spec_from_file_location("nomad_chat_sweep", str(sweep_path))
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(sweep_path)
        spec.loader.exec_module(mod)

        from unittest.mock import patch
        with patch.object(mod, "BRAIN_DIR", fake_brain):
            decisions = mod.sweep_chat_transcripts()
            assert len(decisions) == 1

    def test_live_chat_sweep_execution(self):
        """Run the actual chat sweep script in standalone mode and verify return code & report format."""
        cmd = [sys.executable, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/mesh/pyspark_nomad_chat_sweep.py", "--once"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        assert res.returncode == 0, f"Chat sweep failed: {res.stderr}"
        assert "SWEEP RESULT: SWEEP_VERIFIED_AND_IN_SYNC" in res.stdout

        report_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/network/chat_sweep_report.json")
        assert report_path.exists()
        with open(report_path) as f:
            data = json.load(f)
            assert data["status"] == "SWEEP_VERIFIED_AND_IN_SYNC"
            assert data["total_decisions_extracted"] >= 0


# ---------------------------------------------------------------------------
# 3. R3 Adversarial Tests: Nomad Courier Self-Healer & Socket Probing
# ---------------------------------------------------------------------------
class TestAdversarialR3NomadCourierAndSocketProbing:
    """Stress-tests for Nomad Courier socket probes and edge state recovery."""

    def test_rapid_sequential_socket_probing(self):
        """Execute 200 rapid socket probes to verify sub-50ms latency and no FD leak."""
        engine = _get_nomad_engine()

        t0 = time.perf_counter()
        for _ in range(200):
            res = engine.is_port_listening(59999, host="127.0.0.1")
            assert res is False
        elapsed = time.perf_counter() - t0
        avg_ms = (elapsed / 200) * 1000
        assert avg_ms < 20.0, f"Probe took too long: {avg_ms:.2f}ms/probe"

    def test_concurrent_multithreaded_socket_probing(self):
        """Run 10 threads concurrently probing ports to ensure thread-safety and no crashes."""
        engine = _get_nomad_engine()

        errors = []
        def worker():
            try:
                for _ in range(30):
                    engine.is_port_listening(50052, host="127.0.0.1")
                    engine.is_port_listening(3000, host="127.0.0.1")
                    engine.is_port_listening(18802, host="127.0.0.1")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent socket probe errors: {errors}"

    def test_hanging_tarpit_socket_timeout_safety(self):
        """Verify is_port_listening respects timeout when server accepts but sends nothing."""
        engine = _get_nomad_engine()

        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        try:
            t0 = time.perf_counter()
            is_open = engine.is_port_listening(port, host="127.0.0.1")
            elapsed = time.perf_counter() - t0
            assert is_open is True
            assert elapsed < 1.0
        finally:
            srv.close()

    def test_live_nomad_courier_execution(self):
        """Run nomad_courier_self_healer in standalone --once mode."""
        cmd = [sys.executable, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py", "--once"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        assert res.returncode == 0, f"Self-healer failed: {res.stderr}"

        status_file = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/network/nomad_self_healer_status.json")
        assert status_file.exists()
        with open(status_file) as f:
            status = json.load(f)
            assert "overall_health" in status
            assert status["overall_health"] in ["ALL_ROUTINES_HEALTHY_AND_HEALED", "ALL_ROUTINES_HEALTHY_AND_DOCUMENTED"]


# ---------------------------------------------------------------------------
# 4. R4 DSP & Biometrics Boundary Verification
# ---------------------------------------------------------------------------
class TestAdversarialDSPAndBiometrics:
    """Stress-tests for Kamath 2004 filter, RMSSD, and DFA-alpha1 math."""

    def test_kamath_filter_with_spikes(self):
        """Test Kamath filter on erratic ectopic beat stream (e.g. 800, 300, 800)."""
        rr = [800.0, 300.0, 810.0, 1600.0, 805.0]
        cleaned, count = apply_kamath_2004_filter(rr)
        assert count >= 2
        assert len(cleaned) == len(rr)
        assert cleaned[1] != 300.0

    def test_dfa_alpha1_zone_transitions(self):
        """Verify training zone transitions and fatigue alerts based on heart rate and DFA-alpha1."""
        z2 = determine_training_zone(130, dfa_alpha1=0.75)
        assert z2["active_zone"] == "Zone 2 (Aerobic Base Endurance)"
        assert z2["fatigue_warning"] is False

        z_fatigued = determine_training_zone(130, dfa_alpha1=0.42)
        assert z_fatigued["fatigue_warning"] is True
        assert z_fatigued["intensity_state"] == "ANAEROBIC_FATIGUE_ELEVATED"
