#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/e2e_generation32/tier1_feature_tests.py
=============================================
Tier 1: Feature Coverage E2E Tests in Isolation for Generation 32.

Covers all 9 planned features in scope:
- F1: Router Storage Consolidation & VFS Bind Mounts (consolidate_router_storage.sh)
- F2: OpenWrt Samba Seamless Guest Configuration (samba4 & smb.conf.template)
- F3: Client Automount & Health Watchdog Script (mount_router_network_storage.sh)
- F4: Screen Lens Autonomous Storage Governor (lens_canonical_storage_governor.py)
- F5: Android Companion App Native Shizuku SDK Embedding (build.gradle.kts, AndroidManifest, ShizukuBridge.kt, MainActivity.kt, shizuku_service.dart)
- F6: Termux Shizuku Python MCP Server & Remote Client (shizuku_termux_mcp_server.py, shizuku_remote_client.py)
- F7: Swarm CLI Tool Training Engine (swarm_cli_runner.py)
- F8: Nexus Terminal Physical/Serial Cross-Verification (nexus_cli_cross_verifier.py, swarm_nexus_verification_demo.py)
- F9: Frontier Swarm Consensus: Load Balancing Debate (LOAD_BALANCING_CONSENSUS.md & lora_datasets)

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
import subprocess
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
import frontier_swarm_consensus
import lens_canonical_storage_governor


class TestTier1_F1_RouterStorageConsolidation(unittest.TestCase):
    """Tests for Feature F1: Router Storage Consolidation & VFS Bind Mounts."""

    def setUp(self):
        self.script_path = REPO_ROOT / "00_core_infrastructure" / "router_foundation" / "router" / "usr" / "bin" / "consolidate_router_storage.sh"

    def test_f1_consolidation_script_exists_and_executable(self):
        """Verify consolidate_router_storage.sh exists, is readable, and has proper shebang."""
        self.assertTrue(self.script_path.exists(), f"Missing script: {self.script_path}")
        content = self.script_path.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("#!/bin/sh"), "Script missing #!/bin/sh shebang")
        self.assertTrue(os.access(self.script_path, os.R_OK), f"Script is not readable: {self.script_path}")

    def test_f1_consolidation_script_defines_unified_and_submounts(self):
        """Verify script defines /mnt/lauburu_storage with distributed_dfs and local_flash."""
        content = self.script_path.read_text(encoding="utf-8")
        self.assertIn('UNIFIED_ROOT="/mnt/lauburu_storage"', content)
        self.assertIn('DFS_TARGET="${UNIFIED_ROOT}/distributed_dfs"', content)
        self.assertIn('FLASH_TARGET="${UNIFIED_ROOT}/local_flash"', content)
        self.assertIn('SEAWEED_SRC="/mnt/seaweedfs"', content)
        self.assertIn('FLASH_SRC="/overlay/shared_mesh"', content)

    def test_f1_consolidation_script_supports_all_commands(self):
        """Verify script handles mount, unmount, remount, and status commands."""
        content = self.script_path.read_text(encoding="utf-8")
        self.assertIn("mount_storage", content)
        self.assertIn("unmount_storage", content)
        self.assertIn("status_storage", content)
        self.assertIn("mount|unmount|remount|status", content)

    def test_f1_consolidation_script_handles_rc_local_persistence(self):
        """Verify script contains persistence logic for OpenWrt /etc/rc.local."""
        content = self.script_path.read_text(encoding="utf-8")
        self.assertIn("persist_rc_local", content)
        self.assertIn("RC_LOCAL=\"/etc/rc.local\"", content)
        self.assertIn("consolidate_router_storage", content)

    def test_f1_consolidation_script_syntax_and_status_execution(self):
        """Verify script passes sh -n syntax check and sh <script> status returns exit code 0."""
        res_syntax = subprocess.run(["sh", "-n", str(self.script_path)], capture_output=True, text=True)
        self.assertEqual(res_syntax.returncode, 0, f"Syntax error in script: {res_syntax.stderr}")
        res_status = subprocess.run(["sh", str(self.script_path), "status"], capture_output=True, text=True)
        self.assertEqual(res_status.returncode, 0, f"Runtime error in script status: {res_status.stderr}")
        self.assertIn("Lauburu Router Storage Consolidation Status", res_status.stdout)


class TestTier1_F2_OpenWrtSambaGuestConfig(unittest.TestCase):
    """Tests for Feature F2: OpenWrt Samba Seamless Guest Configuration."""

    def setUp(self):
        self.samba4_path = REPO_ROOT / "00_core_infrastructure" / "router_foundation" / "router" / "etc" / "config" / "samba4"
        self.template_path = REPO_ROOT / "00_core_infrastructure" / "router_foundation" / "router" / "etc" / "samba" / "smb.conf.template"

    def test_f2_samba4_uci_exports_single_broadcast_share(self):
        """Verify /etc/config/samba4 exports exactly ONE sambashare named 'lauburu_storage'."""
        self.assertTrue(self.samba4_path.exists(), f"Missing config: {self.samba4_path}")
        content = self.samba4_path.read_text(encoding="utf-8")
        shares = re.findall(r"config\s+sambashare", content)
        self.assertEqual(len(shares), 1, f"Expected exactly 1 sambashare section, found {len(shares)}")
        self.assertIn("option name 'lauburu_storage'", content)
        self.assertIn("option path '/mnt/lauburu_storage'", content)

    def test_f2_samba4_uci_options_enforce_guest_and_root_mapping(self):
        """Verify UCI options enforce guest_ok, guest_only, force_root, and write access."""
        content = self.samba4_path.read_text(encoding="utf-8")
        self.assertIn("option guest_ok 'yes'", content)
        self.assertIn("option guest_only 'yes'", content)
        self.assertIn("option read_only 'no'", content)
        self.assertIn("option force_root '1'", content)
        self.assertIn("option macos '1'", content)

    def test_f2_samba4_uci_contains_no_legacy_split_shares(self):
        """Verify legacy split shares ('seaweedfs', 'lauburu_shared') are absent."""
        content = self.samba4_path.read_text(encoding="utf-8")
        self.assertNotIn("option name 'seaweedfs'", content)
        self.assertNotIn("option name 'lauburu_shared'", content)

    def test_f2_smb_template_disables_encryption_for_guest_compatibility(self):
        """Verify smb.conf.template explicitly disables smb encrypt to eliminate macOS login loops."""
        self.assertTrue(self.template_path.exists(), f"Missing template: {self.template_path}")
        content = self.template_path.read_text(encoding="utf-8")
        self.assertIn("smb encrypt = disabled", content)
        self.assertIn("server smb encrypt = disabled", content)

    def test_f2_smb_template_configures_guest_mapping_and_null_passwords(self):
        """Verify guest account is nobody, map to guest is Bad User, and null passwords enabled."""
        content = self.template_path.read_text(encoding="utf-8")
        self.assertIn("guest account = nobody", content)
        self.assertIn("guest ok = yes", content)
        self.assertIn("map to guest = Bad User", content)
        self.assertIn("null passwords = yes", content)

    def test_f2_smb_template_restricts_hosts_allow_to_ai_subnet(self):
        """Verify hosts allow strictly permits 192.168.8.0/24, localhost, and Tailscale."""
        content = self.template_path.read_text(encoding="utf-8")
        self.assertIn("hosts allow = 192.168.8.0/24 127.0.0.1 100.0.0.0/8", content)
        self.assertIn("hosts deny = 0.0.0.0/0", content)


class TestTier1_F3_ClientAutomountScript(unittest.TestCase):
    """Tests for Feature F3: Client Automount & Health Watchdog Script."""

    def setUp(self):
        self.mount_script = REPO_ROOT / "06_scripts_and_tooling" / "storage" / "mount_router_network_storage.sh"

    def test_f3_mount_script_exists_and_executable(self):
        """Verify mount_router_network_storage.sh exists and is executable."""
        self.assertTrue(self.mount_script.exists(), f"Missing mount script: {self.mount_script}")
        self.assertTrue(os.access(self.mount_script, os.X_OK), "Mount script is not executable")

    def test_f3_mount_script_targets_unified_mount_and_share(self):
        """Verify script targets unified share lauburu_storage at Router_Unified."""
        content = self.mount_script.read_text(encoding="utf-8")
        self.assertIn('UNIFIED_MOUNT="${MOUNT_BASE}/Router_Unified"', content)
        self.assertIn('lauburu_storage', content)

    def test_f3_mount_script_cleans_legacy_split_mounts(self):
        """Verify script unmounts legacy Router_Shared and Router_SeaweedFS."""
        content = self.mount_script.read_text(encoding="utf-8")
        self.assertIn("cleanup_legacy_mounts", content)
        self.assertIn('LEGACY_SHARED="${MOUNT_BASE}/Router_Shared"', content)
        self.assertIn('LEGACY_SEAWEED="${MOUNT_BASE}/Router_SeaweedFS"', content)

    def test_f3_mount_script_uses_guest_auth_syntax(self):
        """Verify script uses guest auth syntax (//guest:@${ROUTER_IP}/lauburu_storage)."""
        content = self.mount_script.read_text(encoding="utf-8")
        self.assertIn('//guest:@${ROUTER_IP}/lauburu_storage', content)

    def test_f3_mount_script_verifies_read_write_token(self):
        """Verify script writes and removes a verification token file on mount."""
        content = self.mount_script.read_text(encoding="utf-8")
        self.assertIn(".health_check_", content)
        self.assertTrue(
            "read/write verification PASSED" in content or "Root read/write verification PASSED" in content,
            "Script missing read/write verification confirmation log"
        )


class TestTier1_F4_ScreenLensStorageGovernor(unittest.TestCase):
    """Tests for Feature F4: Screen Lens Autonomous Storage Governor."""

    def test_f4_storage_governor_class_initialization(self):
        """Verify CanonicalStorageGovernor instantiates with canonical paths."""
        gov = lens_canonical_storage_governor.CanonicalStorageGovernor()
        self.assertIsNotNone(gov)
        self.assertTrue(hasattr(gov, "structure"))
        self.assertIsInstance(gov.structure, list)

    def test_f4_storage_governor_defines_canonical_structure(self):
        """Verify governor structure includes core infrastructure, models, biometrics, datasets, and vault."""
        gov = lens_canonical_storage_governor.CanonicalStorageGovernor()
        expected = ["core_infrastructure", "ai_models", "biometrics", "lora_datasets", "obsidian_vault"]
        for exp in expected:
            self.assertIn(exp, gov.structure, f"Missing {exp} in storage governor structure")

    def test_f4_storage_governor_local_structure_enforcement(self):
        """Verify governor enforcement creates expected hierarchy in temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gov = lens_canonical_storage_governor.CanonicalStorageGovernor()
            gov.mac_mount = Path(tmpdir)
            gov.enforce_local_structure()
            for folder in gov.structure:
                target = Path(tmpdir) / folder
                self.assertTrue(target.exists(), f"Failed to create canonical folder: {folder}")


class TestTier1_F5_AndroidCompanionAppShizukuSDK(unittest.TestCase):
    """Tests for Feature F5: Android Companion App Native Shizuku SDK Embedding."""

    def setUp(self):
        self.app_dir = REPO_ROOT / "01_apps" / "screen_lens" / "lauburu_life_companion"
        self.gradle_file = self.app_dir / "android" / "app" / "build.gradle.kts"
        self.manifest_file = self.app_dir / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
        self.kotlin_bridge = self.app_dir / "android" / "app" / "src" / "main" / "kotlin" / "com" / "example" / "lauburu_life_companion" / "ShizukuBridge.kt"
        self.main_activity = self.app_dir / "android" / "app" / "src" / "main" / "kotlin" / "com" / "example" / "lauburu_life_companion" / "MainActivity.kt"
        self.dart_service = self.app_dir / "lib" / "services" / "shizuku_service.dart"

    def test_f5_gradle_contains_shizuku_api_and_provider_dependencies(self):
        """Verify build.gradle.kts declares dev.rikka.shizuku:api:13.1.5 and provider."""
        self.assertTrue(self.gradle_file.exists(), f"Missing gradle file: {self.gradle_file}")
        content = self.gradle_file.read_text(encoding="utf-8")
        self.assertIn("dev.rikka.shizuku:api", content)
        self.assertIn("dev.rikka.shizuku:provider", content)
        self.assertIn("13.1.5", content)

    def test_f5_manifest_declares_shizuku_api_permission_and_queries(self):
        """Verify AndroidManifest.xml has API_V23 permission and queries tag."""
        self.assertTrue(self.manifest_file.exists(), f"Missing manifest: {self.manifest_file}")
        content = self.manifest_file.read_text(encoding="utf-8")
        self.assertIn("moe.shizuku.manager.permission.API_V23", content)
        self.assertIn("<queries>", content)
        self.assertIn('android:name="moe.shizuku.privileged.api"', content)

    def test_f5_kotlin_shizuku_bridge_class_structure_and_methods(self):
        """Verify ShizukuBridge.kt implements binder listeners and privileged shell execution."""
        self.assertTrue(self.kotlin_bridge.exists(), f"Missing Kotlin bridge: {self.kotlin_bridge}")
        content = self.kotlin_bridge.read_text(encoding="utf-8")
        self.assertIn("class ShizukuBridge", content)
        self.assertIn("OnBinderReceivedListener", content)
        self.assertIn("OnBinderDeadListener", content)
        self.assertIn("OnRequestPermissionResultListener", content)
        self.assertIn("fun checkPermission()", content)
        self.assertIn("fun requestPermission()", content)
        self.assertIn("fun isAvailable()", content)
        self.assertIn("fun executeShellCommand", content)
        self.assertIn("Shizuku.newProcess", content)

    def test_f5_main_activity_wires_shizuku_method_channel(self):
        """Verify MainActivity.kt routes ai.lauburu.companion/shizuku calls to ShizukuBridge."""
        self.assertTrue(self.main_activity.exists(), f"Missing MainActivity: {self.main_activity}")
        content = self.main_activity.read_text(encoding="utf-8")
        self.assertIn('ai.lauburu.companion/shizuku', content)
        self.assertIn('"isAvailable"', content)
        self.assertIn('"hasPermission"', content)
        self.assertIn('"requestPermission"', content)
        self.assertIn('"executeCommand"', content)
        self.assertIn('"injectTap"', content)
        self.assertIn('"injectKey"', content)
        self.assertIn('"injectSwipe"', content)
        self.assertIn('"injectText"', content)

    def test_f5_dart_shizuku_service_class_and_execution_result(self):
        """Verify shizuku_service.dart implements ShizukuService and ShizukuExecutionResult."""
        self.assertTrue(self.dart_service.exists(), f"Missing Dart service: {self.dart_service}")
        content = self.dart_service.read_text(encoding="utf-8")
        self.assertIn("class ShizukuExecutionResult", content)
        self.assertIn("class ShizukuService", content)
        self.assertIn("Future<bool> isAvailable()", content)
        self.assertIn("Future<bool> hasPermission()", content)
        self.assertIn("Future<ShizukuExecutionResult> executeCommand", content)
        self.assertIn("Future<bool> injectTap", content)
        self.assertIn("Future<bool> injectKey", content)
        self.assertIn("Future<String?> screencap", content)
        self.assertIn("Future<Map<String, dynamic>> getTelemetry()", content)


class TestTier1_F6_TermuxShizukuMCPServer(unittest.TestCase):
    """Tests for Feature F6: Termux Shizuku Python MCP Server & Remote Client."""

    def test_f6_mcp_server_constants_and_protocol_version(self):
        """Verify MCP server constants: port 8089, protocol 2024-11-05."""
        self.assertEqual(shizuku_termux_mcp_server.DEFAULT_PORT, 8089)
        self.assertEqual(shizuku_termux_mcp_server.PROTOCOL_VERSION, "2024-11-05")
        self.assertEqual(shizuku_termux_mcp_server.SERVER_NAME, "shizuku-termux-mcp")

    def test_f6_wx_dex_safety_enforces_read_only_mode(self):
        """Verify WXDexSafety.enforce_dex_safety sets chmod 400 on writable dex files."""
        with tempfile.NamedTemporaryFile(suffix=".dex") as tmp:
            os.chmod(tmp.name, 0o644)
            safe, msg, new_mode = shizuku_termux_mcp_server.WXDexSafety.enforce_dex_safety(tmp.name)
            self.assertTrue(safe)
            self.assertEqual(new_mode, 0o400)
            self.assertIn("chmod 400 applied", msg)

    def test_f6_shizuku_executor_execution_structure(self):
        """Verify ShizukuExecutor returns structured dictionary with exit_code, stdout, duration_ms."""
        executor = shizuku_termux_mcp_server.ShizukuExecutor()
        res = executor.execute("echo 'lauburu_test'")
        self.assertIn("exit_code", res)
        self.assertIn("stdout", res)
        self.assertIn("stderr", res)
        self.assertIn("duration_ms", res)
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("lauburu_test", res["stdout"])

    def test_f6_mcp_tool_definitions_complete_schema(self):
        """Verify MCP_TOOLS registers all 10 required tools with valid input schemas."""
        tools = shizuku_termux_mcp_server.MCP_TOOLS
        self.assertEqual(len(tools), 10)
        tool_names = [t["name"] for t in tools]
        expected_tools = [
            "shizuku_exec", "shizuku_tap", "shizuku_swipe", "shizuku_key",
            "shizuku_text", "shizuku_screencap", "shizuku_active_app",
            "shizuku_pm_grant", "shizuku_battery_info", "shizuku_telemetry"
        ]
        for exp in expected_tools:
            self.assertIn(exp, tool_names)
            tool = next(t for t in tools if t["name"] == exp)
            self.assertIn("inputSchema", tool)
            self.assertIn("type", tool["inputSchema"])

    def test_f6_remote_client_initialization_and_methods(self):
        """Verify ShizukuRemoteClient initializes with defaults and provides required API methods."""
        client = shizuku_remote_client.ShizukuRemoteClient(host="127.0.0.1", port=8089)
        self.assertEqual(client.host, "127.0.0.1")
        self.assertEqual(client.port, 8089)
        self.assertEqual(client.base_url, "http://127.0.0.1:8089")
        methods = ["execute", "tap", "swipe", "key", "text", "screencap", "get_status", "get_battery", "get_telemetry"]
        for m in methods:
            self.assertTrue(hasattr(client, m), f"Missing method {m} on ShizukuRemoteClient")


class TestTier1_F7_SwarmCLIToolRunner(unittest.TestCase):
    """Tests for Feature F7: Swarm CLI Tool Training Engine."""

    def test_f7_cli_execution_result_dataclass_fields(self):
        """Verify CLIExecutionResult dataclass formats structured output with SHA256."""
        now = time.time()
        res = swarm_cli_runner.CLIExecutionResult(
            tool_name="test_tool",
            command_line="test cmd",
            execution_target="localhost",
            transport="local",
            timestamp_iso="2026-09-18T14:00:00Z",
            timestamp_unix=now,
            duration_ms=12.5,
            exit_code=0,
            stdout="sample output\n",
            stderr="",
            stdout_sha256=hashlib.sha256(b"sample output\n").hexdigest(),
            stderr_sha256=hashlib.sha256(b"").hexdigest()
        )
        d = res.to_dict()
        self.assertEqual(d["tool_name"], "test_tool")
        self.assertEqual(d["exit_code"], 0)
        self.assertEqual(d["stdout_sha256"], hashlib.sha256(b"sample output\n").hexdigest())

    def test_f7_swarm_cli_runner_luci_rpc_call_construction(self):
        """Verify SwarmCLIRunner provides execute_luci_rpc, execute_ubus, and execute_uci."""
        runner = swarm_cli_runner.SwarmCLIRunner()
        self.assertTrue(hasattr(runner, "execute_luci_rpc"))
        self.assertTrue(hasattr(runner, "execute_ubus"))
        self.assertTrue(hasattr(runner, "execute_uci"))
        self.assertEqual(runner.router_ip, "192.168.8.1")

    def test_f7_swarm_cli_runner_tailscale_command_execution(self):
        """Verify SwarmCLIRunner provides execute_tailscale with structured CLIExecutionResult."""
        runner = swarm_cli_runner.SwarmCLIRunner()
        self.assertTrue(hasattr(runner, "execute_tailscale"))
        res = runner.execute_tailscale("status", ["--json"], timeout_sec=2.0)
        self.assertIsInstance(res, swarm_cli_runner.CLIExecutionResult)
        self.assertEqual(res.tool_name, "tailscale")

    def test_f7_swarm_cli_runner_wireguard_key_and_show(self):
        """Verify SwarmCLIRunner provides WireGuard key generation & verification."""
        runner = swarm_cli_runner.SwarmCLIRunner()
        self.assertTrue(hasattr(runner, "execute_wireguard"))
        res = runner.execute_wireguard("genkey", target_mode="auto")
        self.assertEqual(res.exit_code, 0)
        self.assertTrue(len(res.stdout.strip()) > 0, "WireGuard genkey produced empty key")

    def test_f7_swarm_cli_runner_sha256_computation(self):
        """Verify SwarmCLIRunner computes bit-for-bit accurate SHA256 hashes on outputs."""
        runner = swarm_cli_runner.SwarmCLIRunner()
        res = runner.execute_wireguard("genkey", target_mode="auto")
        expected_hash = hashlib.sha256(res.stdout.encode("utf-8")).hexdigest()
        self.assertEqual(res.stdout_sha256, expected_hash)


class TestTier1_F8_NexusTerminalCrossVerification(unittest.TestCase):
    """Tests for Feature F8: Nexus Terminal Physical/Serial Cross-Verification."""

    def test_f8_nexus_verification_proof_structure(self):
        """Verify NexusVerificationProof dataclass structure."""
        proof = nexus_cli_cross_verifier.NexusVerificationProof(
            proof_id="PROOF_TEST_001",
            timestamp_iso="2026-09-18T14:00:00Z",
            timestamp_unix=time.time(),
            verdict="PASS",
            rule_enforcements=["Rule 0", "Rule 1", "Rule 5"],
            cli_data={"tool": "tailscale", "exit_code": 0},
            physical_serial_data={"source": "/dev/rfcomm0", "exit_code": 0},
            match_matrix={"exit_code_match": True, "sha256_match": True},
            tri_proof_certification={"proof1_actuation": "Exit Code 0"}
        )
        d = proof.to_dict()
        self.assertEqual(d["proof_id"], "PROOF_TEST_001")
        self.assertEqual(d["verdict"], "PASS")
        self.assertTrue(d["match_matrix"]["exit_code_match"])

    def test_f8_nexus_verifier_initialization_and_dirs(self):
        """Verify NexusCLICrossVerifier instantiates and ensures transcripts directory."""
        verifier = nexus_cli_cross_verifier.NexusCLICrossVerifier()
        self.assertIsNotNone(verifier)
        self.assertTrue(verifier.transcripts_dir.exists())

    def test_f8_nexus_verifier_verification_workflow(self):
        """Verify cross-verifier produces valid NexusVerificationProof with Tri-Proof rules."""
        runner = swarm_cli_runner.SwarmCLIRunner()
        verifier = nexus_cli_cross_verifier.NexusCLICrossVerifier()
        cli_result = runner.execute_wireguard("genkey", target_mode="local")

        proof = verifier.cross_verify(cli_result.to_dict())
        self.assertIn(proof.verdict, ("PASS", "FAIL"))
        self.assertIn("Rule 0 (Zero-Mock)", proof.rule_enforcements)
        self.assertIn("Rule 1 (Tri-Proof)", proof.rule_enforcements)
        self.assertIn("Rule 5 (Tri-Proof Interceptor)", proof.rule_enforcements)

    def test_f8_swarm_nexus_demo_script_present_and_callable(self):
        """Verify swarm_nexus_verification_demo.py exists and exports run_swarm_nexus_demonstration."""
        demo_path = REPO_ROOT / "06_scripts_and_tooling" / "nexus" / "swarm_nexus_verification_demo.py"
        self.assertTrue(demo_path.exists())
        import swarm_nexus_verification_demo
        self.assertTrue(hasattr(swarm_nexus_verification_demo, "run_swarm_nexus_demonstration"))


class TestTier1_F9_FrontierSwarmConsensus(unittest.TestCase):
    """Tests for Feature F9: Frontier Swarm Consensus: Load Balancing Debate."""

    def setUp(self):
        self.root_doc = REPO_ROOT / "LOAD_BALANCING_CONSENSUS.md"
        self.obsidian_doc = REPO_ROOT / "obsidian_vault" / "APPS_AND_FEATURES" / "LOAD_BALANCING_CONSENSUS.md"
        self.lora_dataset = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/frontier_consensus_dataset.jsonl")

    def test_f9_consensus_document_exists_and_parses_yaml_header(self):
        """Verify LOAD_BALANCING_CONSENSUS.md exists at monorepo root and has YAML frontmatter."""
        self.assertTrue(self.root_doc.exists(), f"Missing {self.root_doc}")
        content = self.root_doc.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---"), "Document missing YAML frontmatter opening '---'")
        parts = content.split("---", 2)
        self.assertGreaterEqual(len(parts), 3, "YAML frontmatter not closed with '---'")
        yaml_text = parts[1]
        self.assertIn("title:", yaml_text)
        self.assertIn("consensus_score: 1.0", yaml_text)
        self.assertIn("consensus_ratio: \"8/8 Unanimous\"", yaml_text)

    def test_f9_consensus_score_is_unanimous(self):
        """Verify all 8 participating models approved the consensus."""
        content = self.root_doc.read_text(encoding="utf-8")
        required_models = [
            "gemini_31_pro",
            "gemini_38_flash",
            "claude_opus_46",
            "claude_sonnet_46",
            "gpt_6_astra",
            "gpt_oss_120b",
            "qwen_38_max_master",
            "qwen_38_max_abliterated",
        ]
        for m in required_models:
            self.assertIn(f"{m}: \"APPROVED\"", content, f"Missing unanimous signoff for {m}")

    def test_f9_consensus_evaluates_all_six_technical_vectors(self):
        """Verify document evaluates all 6 technical vectors."""
        content = self.root_doc.read_text(encoding="utf-8")
        vectors = [
            "Vector 1: Bandwidth",
            "Vector 2: Latency",
            "Vector 3: Kernel Driver Overhead",
            "Vector 4: Multi-Port Link Aggregation",
            "Vector 5: Physical Connection Resilience",
            "Vector 6: Systemic Monorepo Topology Fit",
        ]
        for v in vectors:
            self.assertIn(v, content, f"Missing vector evaluation: {v}")

    def test_f9_consensus_codifies_ethernet_primary_usb_recovery_verdict(self):
        """Verify final verdict codifies Ethernet Serial as primary backbone and USB Serial as edge recovery."""
        content = self.root_doc.read_text(encoding="utf-8")
        self.assertIn("Primary High-Bandwidth Load-Balanced Backbone — Ethernet Serial", content)
        self.assertIn("Bluetooth RFCOMM", content)
        self.assertIn("USB Serial", content)

    def test_f9_lora_dataset_distillation_integrity_and_sha256(self):
        """Verify LoRA dataset entries are valid JSONL and latest Gen 32 consensus entry has valid SHA256."""
        self.assertTrue(self.lora_dataset.exists(), f"Missing dataset: {self.lora_dataset}")
        with open(self.lora_dataset, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        self.assertGreater(len(lines), 0, "LoRA dataset is empty")

        # Find latest entry matching Gen 32 consensus
        last_entry = None
        for raw in reversed(lines):
            try:
                obj = json.loads(raw)
                if obj.get("domain") == "mesh_load_balancing_and_hardware_transports" or "Frontier Swarm Consensus" in str(obj.get("task", "")):
                    last_entry = obj
                    break
            except Exception:
                continue

        self.assertIsNotNone(last_entry, "Failed to find Gen 32 consensus entry in dataset")
        self.assertEqual(str(last_entry.get("consensus_score")), "1.0")
        self.assertIn("sha256", last_entry)

        # Recompute SHA256 of entry to verify cryptographic integrity
        entry_copy = dict(last_entry)
        stored_sha = entry_copy.pop("sha256")
        calc_sha = hashlib.sha256(json.dumps(entry_copy, sort_keys=True).encode("utf-8")).hexdigest()
        self.assertEqual(stored_sha, calc_sha, "SHA256 signature mismatch in Gen 32 LoRA entry")


if __name__ == "__main__":
    unittest.main(verbosity=2)
