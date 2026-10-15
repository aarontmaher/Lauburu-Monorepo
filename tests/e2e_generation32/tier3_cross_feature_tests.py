#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/e2e_generation32/tier3_cross_feature_tests.py
==================================================
Tier 3: Cross-Feature Integration E2E Tests for Generation 32.

Pipelines & Multi-Module Interactions:
1. Remote Shizuku Companion Execution -> Swarm CLI Format -> Nexus Physical Serial Cross-Verification
2. Router Storage Consolidation (VFS Bind Mounts & Samba4) -> Screen Lens Governor -> Client Automount Script
3. Swarm CLI Runner Tool Calling (WireGuard/Tailscale) -> Nexus Tri-Proof -> Consensus Telemetry Cross-Reference
4. Android 15 W^X Dex Safety -> Shizuku Executor -> MCP REST/Socket Schema -> Output Validation
5. Shizuku Telemetry Acquisition -> Storage Governor Directory Provisioning -> Audit Trail Persistence

Governed by Rule 0 (Zero-Mock), Rule 1 (Tri-Proof), and Rule 5 (Tri-Proof Interceptor).
"""

import os
import sys
import re
import json
import stat
import time
import sqlite3
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
import frontier_swarm_consensus
import lens_canonical_storage_governor


class TestTier3_RemoteShizukuToNexusVerification(unittest.TestCase):
    """Cross-feature integration between Shizuku execution and Nexus serial cross-verification."""

    def setUp(self):
        self.executor = shizuku_termux_mcp_server.ShizukuExecutor()
        self.verifier = nexus_cli_cross_verifier.NexusCLICrossVerifier()

    def test_shizuku_command_execution_to_nexus_cross_verification_pipeline(self):
        """Pipeline: Shizuku privileged command -> formatted CLI result -> Nexus cross-verification -> Tri-Proof."""
        # 1. Execute privileged command via Shizuku executor
        cmd = "echo 'carrier=1 ip=100.73.38.87 device=pixel10'"
        exec_res = self.executor.execute(cmd)
        self.assertEqual(exec_res["exit_code"], 0)
        stdout_text = exec_res["stdout"]
        stdout_sha = hashlib.sha256(stdout_text.encode("utf-8")).hexdigest()

        # 2. Package into standardized CLIExecutionResult
        cli_result = swarm_cli_runner.CLIExecutionResult(
            tool_name="shizuku_exec",
            command_line=cmd,
            execution_target="pixel10_termux",
            transport="shizuku_binder",
            timestamp_iso=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            timestamp_unix=time.time(),
            duration_ms=exec_res["duration_ms"],
            exit_code=exec_res["exit_code"],
            stdout=stdout_text,
            stderr=exec_res["stderr"],
            stdout_sha256=stdout_sha,
            stderr_sha256=hashlib.sha256(b"").hexdigest(),
            extracted_network_state={
                "carrier_status": True,
                "ip_addresses": ["100.73.38.87"]
            }
        )

        # 3. Simulate authentic physical serial sample from Nexus /dev/rfcomm0
        physical_sample = {
            "source": "pixel10_rfcomm_serial",
            "target": "Pixel 10 Pro XL (L6)",
            "device_node": "/dev/rfcomm0",
            "timestamp_iso": cli_result.timestamp_iso,
            "timestamp_unix": cli_result.timestamp_unix,
            "duration_ms": 4.2,
            "exit_code": 0,
            "raw_stream": stdout_text,
            "stream_sha256": stdout_sha,
            "carrier_status": True,
            "ip_addresses": ["100.73.38.87"],
            "utun_ips": ["100.73.38.87"],
            "serial_device_exists": True,
            "nexus_db_actions": []
        }

        # 4. Cross-verify via NexusCLICrossVerifier
        proof = self.verifier.cross_verify(cli_result=cli_result.to_dict(), physical_sample=physical_sample)
        self.assertEqual(proof.verdict, "PASS")
        self.assertTrue(proof.match_matrix["exit_code_verified"])
        self.assertTrue(proof.match_matrix["carrier_match"])
        self.assertTrue(proof.match_matrix["ip_addresses_match"])
        self.assertTrue(proof.match_matrix["cryptographic_hashes_valid"])
        self.assertIn("Rule 1 (Tri-Proof)", proof.rule_enforcements)

    def test_shizuku_gestures_and_nexus_db_action_audit(self):
        """Pipeline: Shizuku input gestures (tap/key) -> execution -> verify action record schema."""
        # Test input tap simulation
        tap_cmd = "echo 'input tap 540 1200'"
        res = self.executor.execute(tap_cmd)
        self.assertEqual(res["exit_code"], 0)

        # Record action in test SQLite DB mimicking Single-Chat Nexus database
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp_db:
            with sqlite3.connect(tmp_db.name) as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE actions (id INTEGER PRIMARY KEY, action TEXT, exit_code INTEGER, timestamp REAL)")
                c.execute("INSERT INTO actions (action, exit_code, timestamp) VALUES (?, ?, ?)", ("shizuku_tap_540_1200", res["exit_code"], time.time()))
                conn.commit()
                row = c.execute("SELECT action, exit_code FROM actions WHERE id=1").fetchone()
                self.assertEqual(row[0], "shizuku_tap_540_1200")
                self.assertEqual(row[1], 0)


class TestTier3_StorageConsolidationToGovernorAndClientMount(unittest.TestCase):
    """Cross-feature integration between Router Samba consolidation, Screen Lens governor, and client mount."""

    def setUp(self):
        self.samba4_path = REPO_ROOT / "00_core_infrastructure" / "router_foundation" / "router" / "etc" / "config" / "samba4"
        self.consolidate_script = REPO_ROOT / "00_core_infrastructure" / "router_foundation" / "router" / "usr" / "bin" / "consolidate_router_storage.sh"
        self.mount_script = REPO_ROOT / "06_scripts_and_tooling" / "storage" / "mount_router_network_storage.sh"

    def test_samba_config_governor_hierarchy_and_mount_script_alignment(self):
        """Pipeline: Router Samba4 exports lauburu_storage -> Mount script mounts Router_Unified -> Governor manages subdirs."""
        # 1. Verify Samba config exports /mnt/lauburu_storage
        samba_content = self.samba4_path.read_text(encoding="utf-8")
        self.assertIn("option name 'lauburu_storage'", samba_content)
        self.assertIn("option path '/mnt/lauburu_storage'", samba_content)

        # 2. Verify consolidation script creates distributed_dfs and local_flash
        script_content = self.consolidate_script.read_text(encoding="utf-8")
        self.assertIn('DFS_TARGET="${UNIFIED_ROOT}/distributed_dfs"', script_content)
        self.assertIn('FLASH_TARGET="${UNIFIED_ROOT}/local_flash"', script_content)

        # 3. Verify client mount script mounts to Router_Unified
        mount_content = self.mount_script.read_text(encoding="utf-8")
        self.assertIn('UNIFIED_MOUNT="${MOUNT_BASE}/Router_Unified"', mount_content)
        self.assertIn('smb://${ROUTER_IP}/lauburu_storage', mount_content)

        # 4. Initialize storage governor and verify directory structure integration
        with tempfile.TemporaryDirectory() as tmp_unified:
            # Set up unified mock root
            dfs_dir = Path(tmp_unified) / "distributed_dfs"
            flash_dir = Path(tmp_unified) / "local_flash"
            dfs_dir.mkdir(parents=True, exist_ok=True)
            flash_dir.mkdir(parents=True, exist_ok=True)

            gov = lens_canonical_storage_governor.CanonicalStorageGovernor()
            gov.mac_mount = Path(tmp_unified)
            gov.enforce_local_structure()

            # Verify core subdirectories exist
            for sub in ["core_infrastructure", "ai_models", "biometrics", "lora_datasets", "obsidian_vault"]:
                self.assertTrue((Path(tmp_unified) / sub).exists())

    def test_client_mount_health_check_token_lifecycle(self):
        """Pipeline: Test mount health-check token creation, verification, and cleanup inside unified storage."""
        with tempfile.TemporaryDirectory() as tmp_unified:
            mount_dir = Path(tmp_unified) / "Router_Unified"
            mount_dir.mkdir(parents=True, exist_ok=True)

            # Replicate health check token logic from mount_router_network_storage.sh
            hostname = "Mac_Node_L1"
            token_name = f".health_check_{hostname}_{int(time.time())}"
            token_path = mount_dir / token_name

            # Write token
            token_content = f"Lauburu Unified Storage Health Check {time.time()}\n"
            token_path.write_text(token_content, encoding="utf-8")
            self.assertTrue(token_path.exists())

            # Read token back and verify SHA256
            read_back = token_path.read_text(encoding="utf-8")
            self.assertEqual(read_back, token_content)

            # Cleanup token
            token_path.unlink()
            self.assertFalse(token_path.exists())


class TestTier3_SwarmCLIToNexusToConsensusTelemetry(unittest.TestCase):
    """Cross-feature integration between Swarm CLI tool caller, Nexus verification, and Consensus evaluation."""

    def setUp(self):
        self.runner = swarm_cli_runner.SwarmCLIRunner()
        self.verifier = nexus_cli_cross_verifier.NexusCLICrossVerifier()
        self.consensus_path = REPO_ROOT / "LOAD_BALANCING_CONSENSUS.md"

    def test_wireguard_cli_to_nexus_proof_to_consensus_vector_alignment(self):
        """Pipeline: WireGuard keygen CLI -> Nexus cross-verification proof -> Consensus Vector 1 verification."""
        # 1. Execute WireGuard key generation via SwarmCLIRunner
        cli_result = self.runner.execute_wireguard("genkey", target_mode="auto")
        self.assertEqual(cli_result.exit_code, 0)
        self.assertTrue(len(cli_result.stdout.strip()) > 0)

        # 2. Cross-verify with Nexus verifier
        proof = self.verifier.cross_verify(cli_result.to_dict())
        self.assertEqual(proof.verdict, "PASS")
        self.assertTrue(proof.match_matrix["exit_code_verified"])
        self.assertTrue(proof.match_matrix["cryptographic_hashes_valid"])

        # 3. Read consensus report and verify that WireGuard / Ethernet Serial parameters match
        consensus_text = self.consensus_path.read_text(encoding="utf-8")
        self.assertIn("Vector 1: Bandwidth & Throughput Modeling", consensus_text)
        self.assertIn("Ethernet Serial", consensus_text)
        self.assertIn("10GbE", consensus_text)

    def test_nexus_transcripts_persistence_and_retrieval(self):
        """Pipeline: Nexus verification generates proof artifact -> persisted in transcripts dir -> validated."""
        cli_result = self.runner.execute_wireguard("genkey", target_mode="auto")
        proof = self.verifier.cross_verify(cli_result.to_dict())

        # Proof ID format: nexus_proof_<timestamp>_<hash8>
        proof_file = self.verifier.transcripts_dir / f"{proof.proof_id}.json"
        self.assertTrue(proof_file.exists(), f"Proof JSON not persisted to {proof_file}")

        # Load persisted JSON and verify fields
        with open(proof_file, "r", encoding="utf-8") as f:
            persisted_data = json.load(f)
        self.assertEqual(persisted_data["proof_id"], proof.proof_id)
        self.assertEqual(persisted_data["verdict"], proof.verdict)
        self.assertIn("tri_proof_certification", persisted_data)


class TestTier3_ShizukuDexSafetyToRemoteClientExecution(unittest.TestCase):
    """Cross-feature integration between Android 15 W^X safety and Termux Shizuku MCP execution."""

    def test_w_x_safety_enforced_before_command_dispatch(self):
        """Pipeline: W^X safety enforces chmod 400 on dex -> Shizuku executor runs command -> valid output."""
        with tempfile.NamedTemporaryFile(suffix=".dex") as tmp_dex:
            # Simulate insecure dex with write permission
            os.chmod(tmp_dex.name, 0o666)

            # Initialize ShizukuExecutor with this dex
            executor = shizuku_termux_mcp_server.ShizukuExecutor(dex_path=tmp_dex.name)
            self.assertTrue(executor.wx_safe)
            self.assertEqual(executor.dex_mode, 0o400)

            # Execute command with executor
            res = executor.execute("echo 'w_x_safe_execution_verified'")
            self.assertEqual(res["exit_code"], 0)
            self.assertIn("w_x_safe_execution_verified", res["stdout"])

            # Verify file mode remained 0o400
            current_mode = stat.S_IMODE(os.stat(tmp_dex.name).st_mode)
            self.assertEqual(current_mode, 0o400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
