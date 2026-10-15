# -*- coding: utf-8 -*-
"""
Tier 1: Feature Coverage & Contract Verification for verify_probes.py CLI.
Validates multi-transport mesh probing, JSON schema, genuine exit codes, timestamps,
absence of synthetic arrays, and offline node '--' representations.
Governed by: PROJECT.md § Interface Contracts #1, Rule 0, Rule 1, 00_canonical_hardware_matrix.md.
"""
from __future__ import annotations

import json
import sys
import subprocess
from pathlib import Path
import pytest

from .conftest import (
    REPO_ROOT,
    VERIFY_PROBES_PATH,
    PROHIBITED_LITERALS,
    PROBED_TB_SPEED_L1_L2,
    PROBED_ROUTER_MODEL,
    PROBED_ROUTER_FW,
    run_cmd,
)


@pytest.mark.skipif(
    not VERIFY_PROBES_PATH.exists(),
    reason="06_scripts_and_tooling/network/verify_probes.py pending creation by Worker 1",
)
class TestVerifyProbesCli:
    """Verifies the CLI contract, JSON schema, and zero-mock output of verify_probes.py."""

    def test_verify_probes_help_option(self):
        """Asserts that --help displays usage with --json, --output, and exits 0."""
        code, stdout, stderr = run_cmd([sys.executable, str(VERIFY_PROBES_PATH), "--help"])
        assert code == 0, f"--help failed with code {code}: {stderr}"
        assert "--json" in stdout or "-j" in stdout, "Missing --json option in help output"
        assert "--output" in stdout or "-o" in stdout, "Missing --output option in help output"

    def test_verify_probes_cli_json_schema(self):
        """Asserts that --json produces valid JSON matching the PROJECT.md schema."""
        code, stdout, stderr = run_cmd(
            [sys.executable, str(VERIFY_PROBES_PATH), "--json", "--timeout", "5"],
            timeout=35.0,
        )
        assert code == 0, f"verify_probes.py --json failed with code {code}: {stderr}"
        assert stdout.strip(), "verify_probes.py --json produced empty stdout"

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as err:
            pytest.fail(f"verify_probes.py --json output is not valid JSON: {err}\nOutput: {stdout[:500]}")

        # Root level contract
        assert "timestamp" in payload, f"Missing 'timestamp' in JSON root: {payload.keys()}"
        assert "nodes" in payload, f"Missing 'nodes' in JSON root: {payload.keys()}"
        assert isinstance(payload["nodes"], dict), "'nodes' field must be a dictionary"

        nodes = payload["nodes"]
        # Required mesh entities
        expected_nodes = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "GW"]
        for node_id in expected_nodes:
            assert node_id in nodes, f"Missing node {node_id} in nodes dictionary: {list(nodes.keys())}"
            node_data = nodes[node_id]
            assert isinstance(node_data, dict), f"Node {node_id} data must be a dictionary"
            assert "status" in node_data, f"Node {node_id} missing 'status'"
            assert "measured" in node_data, f"Node {node_id} missing 'measured' flag"
            assert isinstance(node_data["measured"], bool), f"Node {node_id} 'measured' must be bool"

        # Offline node contracts (L4 tablet, L7 S20 must be OFFLINE with measured=False)
        for offline_id in ["L4", "L7"]:
            if offline_id in nodes:
                assert nodes[offline_id]["measured"] is False, f"Offline node {offline_id} reported measured=True"
                assert nodes[offline_id]["status"] in ("OFFLINE", "UNREACHABLE"), (
                    f"Offline node {offline_id} reported status: {nodes[offline_id]['status']}"
                )

        # L1 (Mac Mini Host) must be ONLINE and measured=True
        assert nodes["L1"]["status"] == "ONLINE", f"Host L1 status is {nodes['L1']['status']}"
        assert nodes["L1"]["measured"] is True, "Host L1 measured is not True"

    def test_verify_probes_absence_of_synthetic_arrays_and_prohibited_literals(self):
        """Asserts that output contains zero prohibited literals or fabricated hardware claims."""
        code, stdout, stderr = run_cmd(
            [sys.executable, str(VERIFY_PROBES_PATH), "--json", "--timeout", "5"],
            timeout=35.0,
        )
        assert code == 0, f"Execution failed with code {code}: {stderr}"

        payload = json.loads(stdout)
        json_str = json.dumps(payload)

        # Prohibited constants inspection
        for bad_lit in PROHIBITED_LITERALS:
            assert bad_lit not in json_str, (
                f"Prohibited fabricated literal '{bad_lit}' detected in probe output JSON!"
            )

        # Canonical hardware truth validations
        nodes = payload.get("nodes", {})
        # L2 Thunderbolt link speed must be 40 (or 20) if measured
        l2 = nodes.get("L2", {})
        if l2.get("measured") and "tb_speed_gbps" in l2 and l2["tb_speed_gbps"] is not None:
            assert l2["tb_speed_gbps"] in [20, 40] or str(l2["tb_speed_gbps"]) in ["20", "40"], (
                f"L2 Thunderbolt speed reported as {l2['tb_speed_gbps']} Gbps, but probed truth is 40 Gb/s!"
            )

        # Gateway model must be GL-BE14000 if measured (never GL-MT3600BE)
        gw = nodes.get("GW", {})
        if gw.get("measured") and "model" in gw and gw["model"] is not None:
            assert "BE14000" in gw["model"], (
                f"Gateway model reported as '{gw['model']}', expected GL-BE14000"
            )

    def test_verify_probes_table_output_and_placeholders(self):
        """Asserts that stdout table formats offline/unmeasured metrics with '--'."""
        code, stdout, stderr = run_cmd(
            [sys.executable, str(VERIFY_PROBES_PATH), "--timeout", "5"],
            timeout=35.0,
        )
        assert code == 0, f"Table output failed with code {code}: {stderr}"
        assert stdout.strip(), "Stdout is empty"

        # The table must render '--' for offline nodes (e.g. L4, L7)
        assert "--" in stdout, "Table output does not render '--' for missing/offline data"

        # Must display node rows
        for node_id in ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "GW"]:
            assert node_id in stdout, f"Node {node_id} missing from terminal table output"

    def test_verify_probes_output_file_argument(self, tmp_path):
        """Asserts that --output <path> properly serializes probe results to the given file."""
        out_file = tmp_path / "probe_results.json"
        code, stdout, stderr = run_cmd(
            [sys.executable, str(VERIFY_PROBES_PATH), "--json", "--output", str(out_file), "--timeout", "5"],
            timeout=35.0,
        )
        assert code == 0, f"Execution failed with code {code}: {stderr}"
        assert out_file.is_file(), f"Output file not written at: {out_file}"
        assert out_file.stat().st_size > 0, "Output file is empty"

        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert "timestamp" in data and "nodes" in data
