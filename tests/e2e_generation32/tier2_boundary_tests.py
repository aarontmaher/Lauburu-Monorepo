#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/e2e_generation32/tier2_boundary_tests.py
=============================================
Tier 2: Boundary, Corner Case, and Adversarial E2E Tests for Generation 32.

Adversarial Verification Categories:
1. Credential Prompt Prevention & Auth Boundary Integrity
2. Android 15 W^X Memory Safety & Dex Permission Boundary Integrity
3. Shizuku Shell Executor Corner Cases & Adversarial Metacharacters
4. Swarm CLI Runner Boundaries & Timeout Enforcement
5. Nexus Verifier Fail-Closed Integrity & Checksum Mismatch Detection
6. Remote Companion Client Failure Cascades & Unreachable Host Handling
7. Storage Governor Edge Conditions & Directory Permissions

Governed by Rule 0 (Zero-Mock), Rule 1 (Tri-Proof), and Rule 5 (Tri-Proof Interceptor).
"""

import os
import sys
import re
import stat
import json
import time
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Module search paths
for p in [
    REPO_ROOT / "01_apps" / "screen_lens" / "android",
    REPO_ROOT / "01_apps" / "screen_lens" / "src",
    REPO_ROOT / "06_scripts_and_tooling" / "network",
    REPO_ROOT / "06_scripts_and_tooling" / "nexus",
    REPO_ROOT / "06_scripts_and_tooling" / "ai",
    REPO_ROOT / "06_scripts_and_tooling" / "storage",
]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import shizuku_termux_mcp_server
import shizuku_remote_client
import swarm_cli_runner
import nexus_cli_cross_verifier
import lens_canonical_storage_governor


class TestTier2_CredentialPromptPrevention(unittest.TestCase):
    """Adversarial testing of Samba configuration and mount script to ensure zero credential prompts."""

    def setUp(self):
        self.samba4_path = REPO_ROOT / "00_core_infrastructure" / "router_foundation" / "router" / "etc" / "config" / "samba4"
        self.template_path = REPO_ROOT / "00_core_infrastructure" / "router_foundation" / "router" / "etc" / "samba" / "smb.conf.template"
        self.mount_script = REPO_ROOT / "06_scripts_and_tooling" / "storage" / "mount_router_network_storage.sh"

    def test_guest_mapping_behavior_with_arbitrary_user_headers(self):
        """Verify Samba template maps any unknown user (guest, anonymous, nobody, root, arbitrary) to guest account."""
        content = self.template_path.read_text(encoding="utf-8")
        self.assertIn("map to guest = Bad User", content)
        self.assertIn("guest account = nobody", content)
        self.assertIn("null passwords = yes", content)

    def test_samba_uci_forces_guest_only_mode(self):
        """Verify UCI config sets guest_only = yes and force_root = 1 to eliminate interactive authentication."""
        content = self.samba4_path.read_text(encoding="utf-8")
        self.assertIn("option guest_only 'yes'", content)
        self.assertIn("option force_root '1'", content)
        self.assertIn("option guest_ok 'yes'", content)

    def test_encryption_disabled_prevents_spnego_negotiation_loop(self):
        """Verify SMB encryption is disabled on both client and server sides."""
        content = self.template_path.read_text(encoding="utf-8")
        self.assertIn("smb encrypt = disabled", content)
        self.assertIn("server smb encrypt = disabled", content)

    def test_mount_script_uses_explicit_zero_password_syntax(self):
        """Verify mount script executes mount_smbfs with //guest:@ URI preventing terminal password prompts."""
        content = self.mount_script.read_text(encoding="utf-8")
        self.assertIn('//guest:@', content)
        self.assertNotIn('read -s -p "Password"', content)
        self.assertNotIn('passwd', content)

    def test_subnet_allowlist_blocks_unauthorized_ip_space(self):
        """Verify template denies 0.0.0.0/0 while permitting only the local mesh subnets."""
        content = self.template_path.read_text(encoding="utf-8")
        self.assertIn("hosts allow = 192.168.8.0/24 127.0.0.1 100.0.0.0/8", content)
        self.assertIn("hosts deny = 0.0.0.0/0", content)


class TestTier2_Android15_WXDexSafety(unittest.TestCase):
    """Boundary tests for Android 14/15 W^X memory safety rules on rish_shizuku.dex."""

    def test_wx_dex_safety_writable_world_bits_enforces_chmod_400(self):
        """Verify file with mode 0o666 is detected as writable and restricted to 0o400."""
        with tempfile.NamedTemporaryFile(suffix=".dex") as tmp:
            os.chmod(tmp.name, 0o666)
            safe, msg, new_mode = shizuku_termux_mcp_server.WXDexSafety.enforce_dex_safety(tmp.name)
            self.assertTrue(safe)
            self.assertEqual(new_mode, 0o400)
            self.assertIn("chmod 400 applied", msg)
            current_mode = stat.S_IMODE(os.stat(tmp.name).st_mode)
            self.assertEqual(current_mode, 0o400)

    def test_wx_dex_safety_writable_group_bits_enforces_chmod_400(self):
        """Verify file with mode 0o640 is detected as writable and restricted to 0o400."""
        with tempfile.NamedTemporaryFile(suffix=".dex") as tmp:
            os.chmod(tmp.name, 0o640)
            safe, msg, new_mode = shizuku_termux_mcp_server.WXDexSafety.enforce_dex_safety(tmp.name)
            self.assertTrue(safe)
            self.assertEqual(new_mode, 0o400)
            current_mode = stat.S_IMODE(os.stat(tmp.name).st_mode)
            self.assertEqual(current_mode, 0o400)

    def test_wx_dex_safety_already_readonly_0400_is_accepted(self):
        """Verify file already in mode 0o400 passes without redundant modification."""
        with tempfile.NamedTemporaryFile(suffix=".dex") as tmp:
            os.chmod(tmp.name, 0o400)
            safe, msg, new_mode = shizuku_termux_mcp_server.WXDexSafety.enforce_dex_safety(tmp.name)
            self.assertTrue(safe)
            self.assertEqual(new_mode, 0o400)
            self.assertIn("already W^X safe", msg)

    def test_wx_dex_safety_readonly_0444_is_accepted(self):
        """Verify file in mode 0o444 (read-only for user, group, other) passes as safe."""
        with tempfile.NamedTemporaryFile(suffix=".dex") as tmp:
            os.chmod(tmp.name, 0o444)
            safe, msg, new_mode = shizuku_termux_mcp_server.WXDexSafety.enforce_dex_safety(tmp.name)
            self.assertTrue(safe)
            self.assertEqual(new_mode, 0o444)
            self.assertIn("already W^X safe", msg)

    def test_wx_dex_safety_missing_file_handling(self):
        """Verify nonexistent file path fails gracefully without unhandled exception."""
        nonexistent = "/nonexistent/path/to/rish_shizuku.dex"
        safe, msg, mode = shizuku_termux_mcp_server.WXDexSafety.enforce_dex_safety(nonexistent)
        self.assertFalse(safe)
        self.assertIsNone(mode)
        self.assertIn("not found", msg)

    def test_wx_dex_safety_none_path_handling(self):
        """Verify None path fails gracefully without unhandled exception."""
        safe, msg, mode = shizuku_termux_mcp_server.WXDexSafety.enforce_dex_safety(None)
        self.assertFalse(safe)
        self.assertIsNone(mode)


class TestTier2_ShizukuShellExecutorBoundaries(unittest.TestCase):
    """Adversarial and boundary test cases for ShizukuExecutor."""

    def setUp(self):
        self.executor = shizuku_termux_mcp_server.ShizukuExecutor()

    def test_executor_command_timeout_enforcement(self):
        """Verify command exceeding timeout_sec is forcibly terminated with exit_code -4."""
        t_start = time.perf_counter()
        res = self.executor.execute("sleep 2", timeout_sec=1)
        t_elapsed = time.perf_counter() - t_start
        self.assertEqual(res["exit_code"], -4)
        self.assertIn("timed out", res["stderr"])
        self.assertLess(t_elapsed, 2.5, "Executor blocked beyond timeout window")

    def test_executor_nonexistent_command(self):
        """Verify non-existent command returns standard shell 127 exit code and stderr."""
        res = self.executor.execute("lauburu_nonexistent_binary_xyz_12345")
        self.assertEqual(res["exit_code"], 127)
        self.assertTrue(len(res["stderr"]) > 0)

    def test_executor_shell_metacharacters_preservation(self):
        """Verify execution handles quotes, variables, pipes, and control operators safely."""
        complex_cmd = "echo 'foo' | tr 'o' 'u' && echo 'bar;baz&qux'"
        res = self.executor.execute(complex_cmd)
        self.assertEqual(res["exit_code"], 0)
        lines = [l.strip() for l in res["stdout"].splitlines() if l.strip()]
        self.assertEqual(lines, ["fuu", "bar;baz&qux"])

    def test_executor_empty_command_handling(self):
        """Verify empty command string returns exit code 0 without raising exception."""
        res = self.executor.execute("")
        self.assertEqual(res["exit_code"], 0)
        self.assertEqual(res["stdout"], "")

    def test_executor_large_output_stream(self):
        """Verify executor handles 64KB stdout stream without deadlocking pipe buffers."""
        res = self.executor.execute("python3 -c 'print(\"A\" * 65536)'")
        self.assertEqual(res["exit_code"], 0)
        self.assertGreaterEqual(len(res["stdout"]), 65536)

    def test_executor_exit_code_propagation(self):
        """Verify arbitrary exit codes (e.g. 42, 255) are correctly returned."""
        res = self.executor.execute("sh -c 'exit 42'")
        self.assertEqual(res["exit_code"], 42)


class TestTier2_SwarmCLIRunnerBoundaries(unittest.TestCase):
    """Boundary and error handling tests for SwarmCLIRunner."""

    def setUp(self):
        self.runner = swarm_cli_runner.SwarmCLIRunner()

    def test_tailscale_invalid_subcommand_returns_structured_error(self):
        """Verify invalid Tailscale subcommand returns CLIExecutionResult with non-zero exit code."""
        res = self.runner.execute_tailscale("nonexistent_subcommand_9999", timeout_sec=2.0)
        self.assertIsInstance(res, swarm_cli_runner.CLIExecutionResult)
        self.assertNotEqual(res.exit_code, 0)
        self.assertEqual(res.tool_name, "tailscale")
        self.assertIn("nonexistent_subcommand_9999", res.command_line)

    def test_wireguard_invalid_subcommand_returns_structured_error(self):
        """Verify invalid WireGuard subcommand returns non-zero exit code."""
        res = self.runner.execute_wireguard("invalid_cmd_xyz", target_mode="auto", timeout_sec=2.0)
        self.assertIsInstance(res, swarm_cli_runner.CLIExecutionResult)
        self.assertNotEqual(res.exit_code, 0)

    def test_luci_rpc_unreachable_endpoint_returns_structured_error(self):
        """Verify LuCI RPC call against unreachable port returns structured failure rather than crashing."""
        custom_runner = swarm_cli_runner.SwarmCLIRunner(router_ip="127.0.0.1", router_port=59998)
        res = custom_runner.execute_luci_rpc("sys", "exec", ["uptime"], timeout_sec=0.5)
        self.assertIsInstance(res, swarm_cli_runner.CLIExecutionResult)
        self.assertNotEqual(res.exit_code, 0)
        self.assertIn("error", res.stderr.lower())

    def test_ubus_call_unreachable_endpoint_returns_structured_error(self):
        """Verify UBUS call against unreachable router returns structured failure."""
        custom_runner = swarm_cli_runner.SwarmCLIRunner(router_ip="127.0.0.1", router_port=59998)
        res = custom_runner.execute_ubus("network.interface.wan", "status", timeout_sec=0.5)
        self.assertIsInstance(res, swarm_cli_runner.CLIExecutionResult)
        self.assertNotEqual(res.exit_code, 0)


class TestTier2_NexusVerifierFailClosedIntegrity(unittest.TestCase):
    """Adversarial tests for NexusCLICrossVerifier to ensure strict fail-closed security."""

    def setUp(self):
        self.verifier = nexus_cli_cross_verifier.NexusCLICrossVerifier()

    def test_verifier_fails_closed_on_ip_mismatch(self):
        """Verify cross-verifier outputs verdict FAIL when IP addresses in CLI stdout differ from physical state."""
        cli_result = {
            "tool_name": "tailscale",
            "command_line": "tailscale ip -4",
            "execution_target": "localhost",
            "transport": "local",
            "timestamp_iso": "2026-09-18T14:00:00Z",
            "timestamp_unix": time.time(),
            "duration_ms": 5.0,
            "exit_code": 0,
            "stdout": "100.119.199.76\n",
            "stderr": "",
            "stdout_sha256": hashlib.sha256(b"100.119.199.76\n").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "extracted_network_state": {"ip_addresses": ["100.119.199.76"]}
        }

        # Corrupted physical sample reporting completely different IP
        corrupt_physical_sample = {
            "source": "nexus_corrupted_serial",
            "target": "localhost",
            "device_node": "/dev/rfcomm0",
            "timestamp_iso": "2026-09-18T14:00:00Z",
            "timestamp_unix": time.time(),
            "duration_ms": 5.0,
            "exit_code": 0,
            "raw_stream": "100.81.92.125\n",
            "stream_sha256": hashlib.sha256(b"100.81.92.125\n").hexdigest(),
            "carrier_status": True,
            "ip_addresses": ["100.81.92.125"],
            "utun_ips": ["100.81.92.125"],
            "serial_device_exists": True,
            "nexus_db_actions": []
        }

        proof = self.verifier.cross_verify(cli_result=cli_result, physical_sample=corrupt_physical_sample)
        self.assertEqual(proof.verdict, "FAIL", "Verifier failed to reject mismatched IP addresses")
        self.assertFalse(proof.match_matrix.get("ip_addresses_match", True))

    def test_verifier_fails_closed_on_cli_exit_code_nonzero(self):
        """Verify verifier returns verdict FAIL when CLI execution failed with exit code != 0."""
        cli_result = {
            "tool_name": "tailscale",
            "command_line": "tailscale bad_cmd",
            "execution_target": "localhost",
            "transport": "local",
            "timestamp_iso": "2026-09-18T14:00:00Z",
            "timestamp_unix": time.time(),
            "duration_ms": 5.0,
            "exit_code": 1,  # Failure!
            "stdout": "",
            "stderr": "unknown command: bad_cmd",
            "stdout_sha256": hashlib.sha256(b"").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"unknown command: bad_cmd").hexdigest(),
            "extracted_network_state": {}
        }

        proof = self.verifier.cross_verify(cli_result=cli_result)
        self.assertEqual(proof.verdict, "FAIL")
        self.assertFalse(proof.match_matrix.get("exit_code_verified", False))

    def test_verifier_fails_closed_on_carrier_down(self):
        """Verify verifier returns verdict FAIL when physical carrier is down (carrier=False)."""
        cli_result = {
            "tool_name": "openwrt_uci",
            "command_line": "uci get network.wan",
            "execution_target": "router",
            "transport": "http_rpc",
            "timestamp_iso": "2026-09-18T14:00:00Z",
            "timestamp_unix": time.time(),
            "duration_ms": 5.0,
            "exit_code": 0,
            "stdout": "carrier=1\n",
            "stderr": "",
            "stdout_sha256": hashlib.sha256(b"carrier=1\n").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "extracted_network_state": {"carrier_status": True}
        }

        carrier_down_sample = {
            "source": "carrier_down_serial",
            "target": "router",
            "device_node": "/dev/rfcomm0",
            "timestamp_iso": "2026-09-18T14:00:00Z",
            "timestamp_unix": time.time(),
            "duration_ms": 5.0,
            "exit_code": 0,
            "raw_stream": "carrier=0\n",
            "stream_sha256": hashlib.sha256(b"carrier=0\n").hexdigest(),
            "carrier_status": False,  # Carrier offline!
            "ip_addresses": [],
            "utun_ips": [],
            "serial_device_exists": True,
            "nexus_db_actions": []
        }

        proof = self.verifier.cross_verify(cli_result=cli_result, physical_sample=carrier_down_sample)
        self.assertEqual(proof.verdict, "FAIL")
        self.assertFalse(proof.match_matrix.get("carrier_match", True))

    def test_verifier_fails_closed_on_invalid_hash(self):
        """Verify verifier fails closed when cryptographic hash is invalid or truncated."""
        cli_result = {
            "tool_name": "test_tool",
            "command_line": "cmd",
            "execution_target": "localhost",
            "exit_code": 0,
            "stdout_sha256": "invalid_truncated_hash",  # Not 64 chars
            "extracted_network_state": {}
        }
        phys_sample = {
            "exit_code": 0,
            "stream_sha256": "b" * 64,
            "carrier_status": True,
            "ip_addresses": [],
            "utun_ips": []
        }
        proof = self.verifier.cross_verify(cli_result, phys_sample)
        self.assertEqual(proof.verdict, "FAIL")
        self.assertFalse(proof.match_matrix.get("cryptographic_hashes_valid", True))

    def test_verifier_handles_empty_cli_stdout_gracefully(self):
        """Verify empty CLI stdout is handled correctly producing a valid proof ID."""
        cli_result = {
            "tool_name": "empty_cmd",
            "command_line": "true",
            "execution_target": "localhost",
            "transport": "local",
            "timestamp_iso": "2026-09-18T14:00:00Z",
            "timestamp_unix": time.time(),
            "duration_ms": 1.0,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "stdout_sha256": hashlib.sha256(b"").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "extracted_network_state": {}
        }
        proof = self.verifier.cross_verify(cli_result=cli_result)
        self.assertIsNotNone(proof)
        self.assertTrue(proof.proof_id.startswith("nexus_proof_"))


class TestTier2_RemoteClientErrorHandling(unittest.TestCase):
    """Boundary tests for ShizukuRemoteClient error handling."""

    def test_remote_client_unreachable_endpoint_returns_structured_error(self):
        """Verify remote client pointed at unreachable port returns error dictionary without unhandled exception."""
        client = shizuku_remote_client.ShizukuRemoteClient(host="127.0.0.1", port=59997, timeout=0.3)
        res = client.execute("id")
        self.assertTrue(isinstance(res, dict))
        self.assertTrue("error" in res or "exit_code" in res)
        if "exit_code" in res:
            self.assertNotEqual(res["exit_code"], 0)

    def test_remote_client_is_available_false_on_down_server(self):
        """Verify is_available returns False when MCP server is offline."""
        client = shizuku_remote_client.ShizukuRemoteClient(host="127.0.0.1", port=59997, timeout=0.3)
        self.assertFalse(client.is_available())


class TestTier2_StorageGovernorBoundaries(unittest.TestCase):
    """Boundary tests for CanonicalStorageGovernor."""

    def test_storage_governor_nonexistent_mount_handling(self):
        """Verify governor handles missing mount paths gracefully without unhandled exception."""
        gov = lens_canonical_storage_governor.CanonicalStorageGovernor()
        gov.mac_mount = Path("/tmp/nonexistent_lauburu_dfs_mount_xyz_12345")
        gov.linux_mount = Path("/tmp/nonexistent_lauburu_dfs_linux_xyz_12345")
        try:
            gov.enforce_local_structure()
        except Exception as e:
            self.fail(f"Governor crashed on nonexistent mount: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
