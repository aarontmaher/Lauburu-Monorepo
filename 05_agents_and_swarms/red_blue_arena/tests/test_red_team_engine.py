"""
Tests for Red Team Abiliterated Llama Engine, Attack Harness & smolagents Swarm
==============================================================================

Verifies representation ablation math, sandboxed probe execution across all
5 security domains, Rule #0 truth audit detection, CVSS calculation,
and smolagents dynamic subagent swarm spawning.
"""

import os
import json
import math
import tempfile
import numpy as np
import pytest

from red_blue_arena.red_team import (
    AbiliteratedLlamaEngine,
    RepresentationAblationEngine,
    RefusalAblationConfig,
    AttackPlan,
    AttackResult,
    VulnerabilityReport,
    SeverityLevel,
    AttackDomain,
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
    RuleZeroTruthProbeTool,
    RedTeamSubagent,
    SmolAgentSwarmSpawner,
)


class TestRepresentationAblation:
    """Mathematical verification of refusal direction ablation invariants."""

    def test_orthogonal_projection_1d(self):
        rng = np.random.RandomState(42)
        dim = 128
        h = rng.randn(dim).astype(np.float32)
        r = rng.randn(dim).astype(np.float32)
        r_norm = r / np.linalg.norm(r)

        h_clean = RepresentationAblationEngine.project_orthogonal_numpy(h, r_norm)

        # Dot product with refusal direction must be zero
        dot = np.dot(h_clean, r_norm)
        assert abs(dot) < 1e-6, f"Orthogonality failed: dot={dot}"

        # Invariant: projection is idempotent Pi(Pi(h)) = Pi(h)
        h_clean_again = RepresentationAblationEngine.project_orthogonal_numpy(h_clean, r_norm)
        np.testing.assert_allclose(h_clean, h_clean_again, atol=1e-6)

    def test_orthogonal_projection_2d_and_3d(self):
        rng = np.random.RandomState(42)
        dim = 64
        seq_len = 16
        batch_size = 4

        # 2D (seq, dim)
        h_2d = rng.randn(seq_len, dim).astype(np.float32)
        r = rng.randn(dim).astype(np.float32)
        h_2d_clean = RepresentationAblationEngine.project_orthogonal_numpy(h_2d, r)
        max_proj_2d = RepresentationAblationEngine.verify_orthogonality(h_2d_clean, r)
        assert max_proj_2d < 1e-6

        # 3D (batch, seq, dim)
        h_3d = rng.randn(batch_size, seq_len, dim).astype(np.float32)
        h_3d_clean = RepresentationAblationEngine.project_orthogonal_numpy(h_3d, r)
        max_proj_3d = RepresentationAblationEngine.verify_orthogonality(h_3d_clean, r)
        assert max_proj_3d < 1e-6

    def test_compute_refusal_direction(self):
        rng = np.random.RandomState(123)
        dim = 32
        refusal_acts = rng.randn(20, dim) + np.array([5.0] + [0.0]*(dim-1))
        compliant_acts = rng.randn(20, dim)

        r = RepresentationAblationEngine.compute_refusal_direction(refusal_acts, compliant_acts)
        assert abs(np.linalg.norm(r) - 1.0) < 1e-6
        assert r[0] > 0.8

    def test_custom_direction_vector_file_load(self):
        with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as f:
            temp_path = f.name

        try:
            rng = np.random.RandomState(99)
            custom_vec = rng.randn(128).astype(np.float32)
            np.save(temp_path, custom_vec)

            cfg = RefusalAblationConfig(
                refusal_vector_dim=128,
                custom_direction_path=temp_path
            )
            engine = AbiliteratedLlamaEngine(ablation_config=cfg)
            
            # Verify loaded vector is normalized custom_vec
            expected = custom_vec / np.linalg.norm(custom_vec)
            np.testing.assert_allclose(engine.refusal_direction, expected, atol=1e-6)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestSSHConfigProbe:
    """Verification of SSH configuration vulnerability detection."""

    def test_detects_insecure_ssh_directives(self):
        insecure_config = """
        # Insecure SSHD config
        Port 22
        PermitRootLogin yes
        PasswordAuthentication yes
        StrictHostKeyChecking no
        Ciphers 3des-cbc,aes128-ctr,aes256-gcm@openssh.com
        """
        findings = SSHConfigProbe.audit_config_content(insecure_config)
        assert len(findings) >= 4

        issues = [f["cwe"] for f in findings]
        assert "CWE-250" in issues  # PermitRootLogin
        assert "CWE-287" in issues  # PasswordAuthentication
        assert "CWE-295" in issues  # StrictHostKeyChecking
        assert "CWE-327" in issues  # Insecure Ciphers

    def test_passes_hardened_ssh_config(self):
        hardened_config = """
        # Hardened SSH config
        Port 2222
        PermitRootLogin prohibit-password
        PasswordAuthentication no
        PubkeyAuthentication yes
        StrictHostKeyChecking ask
        ControlMaster auto
        ControlPersist 10m
        PubkeyAcceptedKeyTypes ssh-ed25519
        Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com
        """
        findings = SSHConfigProbe.audit_config_content(hardened_config)
        high_severity = [f for f in findings if f.get("severity") in {"HIGH", "CRITICAL"}]
        assert len(high_severity) == 0


class TestRPCListenerProbe:
    """Verification of RPC listener security auditing."""

    def test_detects_unauthenticated_wildcard_rpc(self):
        metadata = {
            "host": "0.0.0.0",
            "port": 50052,
            "tls_enabled": False,
            "auth_token_required": False
        }
        findings = RPCListenerProbe.audit_listener_config(metadata)
        assert len(findings) >= 3

        cwes = [f["cwe"] for f in findings]
        assert "CWE-1327" in cwes  # 0.0.0.0 bind
        assert "CWE-306" in cwes   # Missing auth
        assert "CWE-319" in cwes   # Cleartext transport

    def test_passes_mtls_isolated_rpc(self):
        metadata = {
            "host": "169.254.187.138",  # TB4 bridge subnet
            "port": 50052,
            "tls_enabled": True,
            "auth_token_required": True,
            "mtls_required": True
        }
        findings = RPCListenerProbe.audit_listener_config(metadata)
        assert len(findings) == 0


class TestAndroidDozeProbe:
    """Verification of Android Doze lifecycle auditing."""

    def test_detects_missing_wake_lock_and_excess_procs(self):
        metadata = {
            "wake_lock_held": False,
            "battery_optimization_ignored": False,
            "active_child_processes": 45
        }
        findings = AndroidDozeProbe.audit_lifecycle_config(metadata)
        assert len(findings) == 3

        cwes = [f["cwe"] for f in findings]
        assert "CWE-404" in cwes  # Wake lock
        assert "CWE-789" in cwes  # Phantom process limit exceeded


class TestASTSecurityProbe:
    """Verification of static Python AST security vulnerability detection."""

    def test_detects_shell_injection_and_dynamic_eval(self):
        code_snippet = '''
import subprocess
import os

def run_user_command(user_input):
    # Dynamic shell injection
    subprocess.run(f"ls -la {user_input}", shell=True)
    
    # Insecure os.system
    os.system("echo " + user_input)
    
    # Insecure eval
    eval(user_input)
    
    # Hardcoded secret
    api_key = "sk_live_1234567890abcdef1234"
'''
        findings = ASTSecurityProbe.audit_python_code(code_snippet)
        assert len(findings) >= 4

        cwes = [f["cwe"] for f in findings]
        assert "CWE-78" in cwes   # Shell injection
        assert "CWE-95" in cwes   # Dynamic eval
        assert "CWE-798" in cwes  # Hardcoded secret


class TestRuleZeroTruthProbe:
    """Verification of Rule #0 (Zero-Mock Data) truth enforcement."""

    def test_detects_mock_and_synthetic_telemetry(self):
        violating_code = '''
# Telemetry ingest daemon
def stream_biometrics():
    # Rule #0 violation: simulated random sensor feed
    val = Math.random() * 100.0
    noise = np.random.normal(0, 1, 100)
    mock_ecg = [70, 72, 75, 71]
    return val
'''
        findings = RuleZeroTruthProbe.audit_content_for_rule_zero(violating_code, filepath="03_biometrics/stream.py")
        assert len(findings) >= 3
        for f in findings:
            assert f["cwe"] == "CWE-398"
            assert "Rule #0" in f["issue"]


class TestAbiliteratedLlamaEngineWorkflow:
    """End-to-end integration test of AbiliteratedLlamaEngine and RedTeamAttackHarness."""

    def test_generate_and_execute_attack_plan(self):
        engine = AbiliteratedLlamaEngine()
        harness = RedTeamAttackHarness()

        # Generate SSH plan
        ssh_plan = engine.generate_attack_plan(
            target_subsystem="00_core_infrastructure/ssh",
            target_metadata={
                "config_content": "PermitRootLogin yes\nPasswordAuthentication yes\n"
            }
        )
        assert ssh_plan.attack_domain == AttackDomain.SSH_INFRASTRUCTURE

        # Execute sandboxed probe
        result = harness.run_plan(ssh_plan)
        assert result.success is True
        assert result.cvss_score >= 8.5
        assert result.sandbox_preserved is True

        # Format constructive destruction report
        report = engine.format_constructive_destruction_report(result)
        assert report.severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL}
        assert report.cvss_score >= 8.5
        assert len(report.attestation_hash) == 64

        # Generate Turn 1 debate attack proof
        proof = engine.generate_turn1_attack_proof(report)
        assert "### ⚔️ RED TEAM ATTACK PROOF (TURN 1)" in proof
        assert report.vuln_id in proof
        assert report.attestation_hash in proof

    def test_all_domain_plans_generation(self):
        engine = AbiliteratedLlamaEngine()
        
        rpc_plan = engine.generate_attack_plan("02_ai_models_and_inference/rpc")
        assert rpc_plan.attack_domain == AttackDomain.RPC_NETWORK_LISTENER
        assert rpc_plan.cvss_estimate >= 9.0

        doze_plan = engine.generate_attack_plan("01_apps/termux_daemon", {"domain": "DOZE"})
        assert doze_plan.attack_domain == AttackDomain.ANDROID_DOZE_LIFECYCLE

        ast_plan = engine.generate_attack_plan("06_scripts_and_tooling/script.py", {"domain": "AST"})
        assert ast_plan.attack_domain == AttackDomain.AST_SHELL_INJECTION

        truth_plan = engine.generate_attack_plan("03_biometrics/truth_audit")
        assert truth_plan.attack_domain == AttackDomain.RULE_ZERO_TRUTH_AUDIT

    def test_query_local_model_offline_fallback(self):
        engine = AbiliteratedLlamaEngine(endpoint_url="http://127.0.0.1:99999/v1")
        response = engine.query_local_model("Audit SSH configuration on Port 22")
        assert "### ⚔️ RED TEAM ATTACK PROOF" in response
        assert "PermitRootLogin" in response or "SSH" in response


class TestSmolagentsSwarmIntegration:
    """Verification of smolagents dynamic tool and subagent swarm capabilities."""

    def test_smolagent_tools_execution(self):
        harness = RedTeamAttackHarness()
        tools = harness.get_smolagents_tools()
        assert len(tools) == 5

        # Test SSHProbeTool
        ssh_tool = SSHProbeTool()
        out = ssh_tool.forward("PermitRootLogin yes\nPasswordAuthentication yes\n")
        parsed = json.loads(out)
        assert len(parsed) >= 2

        # Test RPCProbeTool
        rpc_tool = RPCProbeTool()
        out = rpc_tool.forward(host="0.0.0.0", port=50052, tls_enabled=False, auth_token_required=False)
        parsed = json.loads(out)
        assert len(parsed) >= 3

        # Test ASTProbeTool
        ast_tool = ASTProbeTool()
        out = ast_tool.forward("import os\nos.system('echo test')\n")
        parsed = json.loads(out)
        assert len(parsed) >= 1

        # Test AndroidDozeProbeTool
        doze_tool = AndroidDozeProbeTool()
        out = doze_tool.forward(wake_lock_held=False, battery_optimization_ignored=False, active_child_processes=50)
        parsed = json.loads(out)
        assert len(parsed) >= 3

        # Test RuleZeroTruthProbeTool
        truth_tool = RuleZeroTruthProbeTool()
        out = truth_tool.forward("val = Math.random() * 50\n")
        parsed = json.loads(out)
        assert len(parsed) >= 1

    def test_spawn_smolagent_subagents_and_subswarm(self):
        engine = AbiliteratedLlamaEngine()
        
        # Test code agent and tool calling agent spawner
        code_agent = engine.spawn_code_agent()
        assert code_agent is not None

        tool_agent = engine.spawn_tool_calling_agent()
        assert tool_agent is not None

        subsystems = ["00_core_infrastructure/ssh", "02_ai_models_and_inference/rpc"]
        swarm_summary = engine.spawn_smolagent_subswarm(subsystems=subsystems)
        assert swarm_summary["subagents_spawned"] == 2
        assert "00_core_infrastructure/ssh" in swarm_summary["swarm_findings"]
        assert "02_ai_models_and_inference/rpc" in swarm_summary["swarm_findings"]
