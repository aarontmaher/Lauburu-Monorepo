#!/usr/bin/env python3
"""
================================================================================
🧪 Unit & Integration Tests: Swarm CLI & Nexus Terminal Verification (Gen 32)
================================================================================
Test Target:
  - 06_scripts_and_tooling/network/swarm_cli_runner.py
  - 06_scripts_and_tooling/nexus/nexus_cli_cross_verifier.py
  - 06_scripts_and_tooling/nexus/swarm_nexus_verification_demo.py
Governed by:
  - Rule 0 (Zero-Mock): Authentic local execution & genuine kernel telemetry
  - Rule 1 (Tri-Proof): Exact exit codes, cryptographic SHA256, empirical verification
  - Rule 5 (Tri-Proof Interceptor Gate): Strict failure on unverified or mismatch claims
================================================================================
"""

import os
import sys
import json
import pytest
import hashlib
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling" / "network"))
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling" / "nexus"))

from swarm_cli_runner import SwarmCLIRunner, CLIExecutionResult
from nexus_cli_cross_verifier import NexusCLICrossVerifier, NexusVerificationProof, TRANSCRIPTS_DIR
from swarm_nexus_verification_demo import run_swarm_nexus_demonstration, REPORT_PATH


@pytest.fixture
def runner():
    return SwarmCLIRunner()


@pytest.fixture
def verifier():
    return NexusCLICrossVerifier()


def test_swarm_cli_runner_initialization(runner):
    """Verifies runner initializes with valid gateway parameters and resolved binaries."""
    assert runner.router_ip == "192.168.8.1"
    assert runner.router_user == "root"
    assert runner.tailscale_bin is not None
    assert os.path.exists(runner.tailscale_bin)
    assert os.access(runner.tailscale_bin, os.X_OK)


def test_tailscale_status_json_execution_and_extraction(runner):
    """Verifies tailscale status --json executes genuinely, returning valid exit code and extracted IPs."""
    res = runner.execute_tailscale("status", ["--json"])
    assert res.exit_code == 0
    assert res.tool_name == "tailscale"
    assert len(res.stdout_sha256) == 64
    assert res.parsed_json is not None
    assert "BackendState" in res.parsed_json
    assert res.extracted_network_state["carrier_status"] is True
    assert len(res.extracted_network_state["ip_addresses"]) > 0


def test_tailscale_ip_v4_returns_valid_format(runner):
    """Verifies tailscale ip -4 returns a valid IPv4 address."""
    res = runner.execute_tailscale("ip", ["-4"])
    assert res.exit_code == 0
    ip_out = res.stdout.strip()
    assert ip_out.count(".") == 3
    assert ip_out in res.extracted_network_state["ip_addresses"]


def test_wireguard_genkey_and_pubkey_cryptographic_parity(runner):
    """Verifies WireGuard key generation and pubkey derivation yields standard 44-char base64 keys."""
    key_res = runner.execute_wireguard("genkey")
    assert key_res.exit_code == 0
    privkey = key_res.stdout.strip()
    assert len(privkey) == 44
    assert privkey.endswith("=")

    pub_res = runner.execute_wireguard("pubkey", stdin_input=privkey)
    assert pub_res.exit_code == 0
    pubkey = pub_res.stdout.strip()
    assert len(pubkey) == 44
    assert pubkey.endswith("=")
    assert len(pub_res.stdout_sha256) == 64


def test_openwrt_ubus_device_status_br_lan(runner):
    """Verifies ubus call network.device status for br-lan retrieves real kernel carrier and counters."""
    res = runner.execute_ubus("network.device", "status", {"name": "br-lan"})
    assert res.exit_code == 0
    assert res.tool_name == "openwrt_ubus"
    assert res.extracted_network_state["carrier_status"] is True
    assert res.extracted_network_state["rx_bytes"] is not None
    assert res.extracted_network_state["rx_bytes"] > 0
    assert res.extracted_network_state["tx_bytes"] is not None
    assert res.extracted_network_state["tx_bytes"] > 0


def test_openwrt_ubus_interface_lan_status(runner):
    """Verifies ubus call network.interface.lan status retrieves router IP 192.168.8.1."""
    res = runner.execute_ubus("network.interface.lan", "status")
    assert res.exit_code == 0
    assert "192.168.8.1" in res.extracted_network_state["ip_addresses"]


def test_nexus_physical_sample_gateway_serial(verifier):
    """Verifies physical serial console sampler extracts real carrier, MAC, and byte counters from router."""
    sample = verifier.sample_gateway_physical_serial()
    assert sample["exit_code"] == 0
    assert sample["carrier_status"] is True
    assert sample["mac_address"] == "94:83:c4:eb:e7:31"
    assert sample["rx_bytes"] is not None and sample["rx_bytes"] > 0
    assert len(sample["stream_sha256"]) == 64


def test_nexus_physical_sample_host_nexus_terminal(verifier):
    """Verifies physical host nexus sampler detects incoming serial port and active en0 interface."""
    sample = verifier.sample_host_nexus_physical()
    assert sample["exit_code"] == 0
    assert sample["carrier_status"] is True
    assert sample["serial_device_exists"] is True
    assert len(sample["utun_ips"]) > 0
    assert len(sample["stream_sha256"]) == 64


def test_nexus_cross_verification_emits_valid_tri_proof(runner, verifier):
    """Verifies cross_verify produces a PASS verdict and persists proof artifact with SHA256 hashes."""
    cli_res = runner.execute_tailscale("status", ["--json"])
    proof = verifier.cross_verify(cli_res.to_dict(), tool_category="tailscale")

    assert isinstance(proof, NexusVerificationProof)
    assert proof.verdict == "PASS"
    assert proof.match_matrix["exit_code_verified"] is True
    assert proof.match_matrix["carrier_match"] is True
    assert proof.match_matrix["ip_addresses_match"] is True
    assert proof.match_matrix["byte_counters_match"] is True
    assert len(proof.tri_proof_certification["proof_1_actuation"]) > 0
    assert len(proof.tri_proof_certification["proof_2_line_by_line"]) > 0

    # Verify JSON proof file exists on disk
    proof_file = TRANSCRIPTS_DIR / f"{proof.proof_id}.json"
    assert proof_file.exists()
    with open(proof_file) as f:
        saved_data = json.load(f)
    assert saved_data["proof_id"] == proof.proof_id
    assert saved_data["verdict"] == "PASS"


def test_nexus_cross_verification_detects_exit_code_failure(verifier):
    """Verifies Rule 1 & Rule 5 Interceptor Gate rejects execution with non-zero exit code."""
    fake_cli_res = {
        "tool_name": "tailscale",
        "command_line": "tailscale bad_command",
        "execution_target": "localhost",
        "exit_code": 1,
        "stdout": "",
        "stderr": "error: command failed",
        "stdout_sha256": hashlib.sha256(b"").hexdigest(),
        "extracted_network_state": {"carrier_status": True, "ip_addresses": ["100.119.199.76"]}
    }
    proof = verifier.cross_verify(fake_cli_res, tool_category="tailscale")
    assert proof.verdict == "FAIL"
    assert proof.match_matrix["exit_code_verified"] is False


def test_nexus_cross_verification_detects_carrier_mismatch(verifier):
    """Verifies Interceptor Gate marks execution as FAIL when carrier status does not match physical truth."""
    cli_res = {
        "tool_name": "ubus",
        "command_line": "ubus call network.device status '{\"name\":\"br-lan\"}'",
        "execution_target": "gw_router",
        "exit_code": 0,
        "stdout": '{"carrier": false}',
        "stdout_sha256": hashlib.sha256(b'{"carrier": false}').hexdigest(),
        "extracted_network_state": {"carrier_status": False, "ip_addresses": ["192.168.8.1"]}
    }
    # Physical gateway carrier is True
    proof = verifier.cross_verify(cli_res, tool_category="ubus")
    assert proof.verdict == "FAIL"
    assert proof.match_matrix["carrier_match"] is False


def test_swarm_nexus_verification_demo_runs_to_completion():
    """Verifies full end-to-end demonstration script executes all 4 stages and generates report."""
    success = run_swarm_nexus_demonstration()
    assert success is True
    assert REPORT_PATH.exists()
    content = REPORT_PATH.read_text()
    assert "status: \"VERIFIED_PASSED\"" in content
    assert "## 2. Tri-Proof Verification Matrix" in content
    assert "UBUS" in content
    assert "TAILSCALE" in content
    assert "WIREGUARD" in content
