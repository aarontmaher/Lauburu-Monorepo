"""
Unit tests for Lauburu Ecosystem 7-Layer Mesh Empirical Verification Probes (verify_probes.py).

Verifies:
1. Zero-Mock measurement envelope structure (value, measured, source_cmd, exit_code, latency_ms, captured_at, error).
2. Live hardware and link-speed probing (system_profiler Thunderbolt speeds, L1 sysctl).
3. Multi-transport fallback hierarchy and offline node handling (null values, '--' display).
4. CLI options (--json, --output, --timeout).
5. Absence of hardcoded mock constants in verify_probes.py.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure monorepo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent

# Dynamically import verify_probes because directory name starts with digits ('06_scripts_and_tooling')
verify_probes_path = REPO_ROOT / "06_scripts_and_tooling" / "network" / "verify_probes.py"
spec = importlib.util.spec_from_file_location("verify_probes", str(verify_probes_path))
verify_probes = importlib.util.module_from_spec(spec)
sys.modules["verify_probes"] = verify_probes
spec.loader.exec_module(verify_probes)

make_measured = verify_probes.make_measured
make_unmeasured = verify_probes.make_unmeasured
clean_cpu_string = verify_probes.clean_cpu_string
parse_ram_gb = verify_probes.parse_ram_gb
probe_thunderbolt_speeds = verify_probes.probe_thunderbolt_speeds
probe_local_l1 = verify_probes.probe_local_l1
probe_ssh_node = verify_probes.probe_ssh_node
probe_tcp_services = verify_probes.probe_tcp_services
probe_mesh = verify_probes.probe_mesh
format_table = verify_probes.format_table


class TestMeasuredEnvelope:
    """Validate compliance with the _measured.py envelope structure."""

    def test_make_measured_valid(self):
        envelope = make_measured(
            value=24.0,
            source_cmd="sysctl -n hw.memsize",
            exit_code=0,
            latency_ms=0.0,
        )
        assert envelope["value"] == 24.0
        assert envelope["measured"] is True
        assert envelope["source_cmd"] == "sysctl -n hw.memsize"
        assert envelope["exit_code"] == 0
        assert envelope["latency_ms"] == 0.0
        assert envelope["error"] is None
        assert isinstance(envelope["captured_at"], float)

    def test_make_measured_with_none_value(self):
        envelope = make_measured(value=None, source_cmd="test_cmd")
        assert envelope["value"] is None
        assert envelope["measured"] is False
        assert envelope["source_cmd"] == "test_cmd"

    def test_make_measured_with_error(self):
        envelope = make_measured(value="data", error="Command timed out")
        assert envelope["measured"] is False
        assert envelope["error"] == "Command timed out"

    def test_make_unmeasured(self):
        envelope = make_unmeasured(
            source_cmd="ssh user@host",
            reason="Host unreachable",
        )
        assert envelope["value"] is None
        assert envelope["measured"] is False
        assert envelope["source_cmd"] == "ssh user@host"
        assert envelope["exit_code"] is None
        assert envelope["latency_ms"] is None
        assert envelope["error"] == "Host unreachable"
        assert isinstance(envelope["captured_at"], float)


class TestHardwareParsing:
    """Validate hardware string cleaning and memory tier normalization."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Apple M4 Pro", "Apple M4 Pro"),
            ("Apple M4", "Apple M4"),
            ("Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz", "Intel i7-9750H"),
            ("AMD Ryzen 7 5700U with Radeon Graphics", "AMD Ryzen 7 5700U"),
            ("Intel(R) Core(TM) i7-8700B CPU @ 3.20GHz", "Intel i7-8700B"),
        ],
    )
    def test_clean_cpu_string(self, raw, expected):
        assert clean_cpu_string(raw) == expected

    @pytest.mark.parametrize(
        "bytes_val,expected_gb",
        [
            (25769803776, 24.0),   # L1: 24GB
            (17179869184, 16.0),   # L2 & L5: 16GB
            (16073752576, 15.0),   # L3: 15GB
            (33492692992, 32.0),   # L8: 32GB
            (2034060 * 1024, 2.0), # GW: 2GB
        ],
    )
    def test_parse_ram_gb(self, bytes_val, expected_gb):
        assert parse_ram_gb(bytes_val) == expected_gb


class TestLiveProbingHarness:
    """Validate live execution against genuine physical host interfaces."""

    def test_probe_local_l1(self):
        res = probe_local_l1(timeout=3.0)
        assert res["status"] == "ONLINE"
        assert res["measured"] is True
        assert res["latency_ms"] == 0.0
        assert res["exit_code"] == 0
        assert res["error"] is None
        assert "Apple" in res["cpu"]
        assert res["ram_gb"] >= 16.0
        assert "cpu" in res["metrics"]
        assert "ram_gb" in res["metrics"]
        assert res["metrics"]["cpu"]["measured"] is True
        assert res["metrics"]["ram_gb"]["measured"] is True

    def test_probe_thunderbolt_speeds(self):
        speeds = probe_thunderbolt_speeds(timeout=5.0)
        assert isinstance(speeds, dict)
        # Empirical probed speeds: L2 = 20 Gb/s, L5 = 40 Gb/s, L8 = 40 Gb/s
        assert speeds.get("L2") == 20
        assert speeds.get("L5") == 40
        assert speeds.get("L8") == 40


class TestMultiTransportFallbackAndOfflineHandling:
    """Validate multi-transport failover and honest offline node accounting."""

    @patch.object(verify_probes, "test_connection")
    @patch("subprocess.run")
    def test_ssh_transport_fallback_to_tailscale(self, mock_subproc, mock_test_conn):
        # TB fails, LAN fails, Tailscale succeeds
        mock_test_conn.side_effect = [
            (False, None),  # TB
            (False, None),  # LAN
            (True, 15.5),   # Tailscale
        ]
        mock_subproc.return_value = MagicMock(
            returncode=0,
            stdout="Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz\n---METRIC---\n17179869184\n---METRIC---\nuptime",
            stderr="",
        )

        node_data = probe_ssh_node(
            node_key="L2",
            user="aaronmaher",
            transports=[
                ("thunderbolt", "fe80::1", 22),
                ("lan", "192.168.8.127", 22),
                ("tailscale", "100.103.212.21", 22),
            ],
            cmd="probe_cmd",
            tb_speed=20,
            timeout=2.0,
        )

        assert node_data["status"] == "ONLINE"
        assert node_data["measured"] is True
        assert node_data["transport"] == "tailscale"
        assert node_data["latency_ms"] == 15.5
        assert node_data["cpu"] == "Intel i7-9750H"
        assert node_data["ram_gb"] == 16.0
        assert node_data["tb_speed_gbps"] == 20

    @patch.object(verify_probes, "test_connection")
    def test_all_transports_fail_marks_offline(self, mock_test_conn):
        mock_test_conn.return_value = (False, None)

        node_data = probe_ssh_node(
            node_key="L4",
            user="user",
            transports=[
                ("lan", "192.168.8.116", 22),
                ("tailscale", "100.118.79.63", 22),
            ],
            cmd="probe_cmd",
            timeout=1.0,
        )

        assert node_data["status"] == "OFFLINE"
        assert node_data["measured"] is False
        assert node_data["value"] is None
        assert node_data["cpu"] is None
        assert node_data["ram_gb"] is None
        assert node_data["latency_ms"] is None
        assert "unreachable" in node_data["error"]
        assert node_data["metrics"]["cpu"]["measured"] is False

    @patch.object(verify_probes, "test_connection")
    def test_tcp_services_probe_partial_and_offline(self, mock_test_conn):
        # Port 3035 and 8022 succeed, others fail
        def side_effect(host, port, **kwargs):
            if port in [3035, 8022]:
                return True, 8.5
            return False, None

        mock_test_conn.side_effect = side_effect

        res = probe_tcp_services(
            hosts=["192.168.8.213"],
            ports=[3035, 50052, 8022, 5555],
            timeout=1.0,
        )
        assert res["status"] == "PARTIAL"
        assert res["measured"] is True
        assert res["ports"] == [3035, 8022]
        assert res["latency_ms"] == 8.5

        # When all fail
        mock_test_conn.side_effect = lambda *args, **kwargs: (False, None)
        res_offline = probe_tcp_services(
            hosts=["192.168.8.213"],
            ports=[3035, 50052],
            timeout=1.0,
        )
        assert res_offline["status"] == "OFFLINE"
        assert res_offline["measured"] is False
        assert res_offline["ports"] == []

    @patch.object(verify_probes, "test_connection")
    @patch("subprocess.run")
    def test_ssh_node_thunderbolt_none_when_unprobed(self, mock_subproc, mock_test_conn):
        mock_test_conn.return_value = (True, 5.0)
        mock_subproc.return_value = MagicMock(
            returncode=0,
            stdout="Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz\n---METRIC---\n17179869184\n---METRIC---\nuptime",
            stderr="",
        )
        node_data = probe_ssh_node(
            node_key="L2",
            user="aaronmaher",
            transports=[("lan", "192.168.8.127", 22)],
            cmd="probe_cmd",
            tb_speed=None,
            timeout=2.0,
        )
        assert node_data["status"] == "ONLINE"
        assert node_data["tb_speed_gbps"] is None
        assert node_data["metrics"]["tb_speed_gbps"]["measured"] is False
        assert node_data["metrics"]["tb_speed_gbps"]["value"] is None

    @patch.object(verify_probes, "test_connection")
    @patch("subprocess.run")
    def test_gw_router_unparseable_mem_returns_none_and_unmeasured(self, mock_subproc, mock_test_conn):
        mock_test_conn.return_value = (True, 2.0)
        mock_subproc.return_value = MagicMock(
            returncode=0,
            stdout="GL-BE14000\n---METRIC---\nOpenWrt 21.02-SNAPSHOT\n---METRIC---\ncorrupted memory output\n---METRIC---\nuptime",
            stderr="",
        )
        gw_data = probe_ssh_node(
            node_key="GW",
            user="root",
            transports=[("lan", "192.168.8.1", 22)],
            cmd="probe_cmd",
            timeout=2.0,
        )
        assert gw_data["status"] == "ONLINE"
        assert gw_data["ram_gb"] is None
        assert gw_data["value"]["ram_gb"] is None
        assert gw_data["metrics"]["ram_gb"]["measured"] is False
        assert gw_data["metrics"]["ram_gb"]["value"] is None

    @patch.object(verify_probes, "test_connection")
    @patch("subprocess.run")
    def test_gw_router_meminfo_fallback_parses_correctly(self, mock_subproc, mock_test_conn):
        mock_test_conn.return_value = (True, 2.0)
        mock_subproc.return_value = MagicMock(
            returncode=0,
            stdout="GL-BE14000\n---METRIC---\nOpenWrt 21.02-SNAPSHOT\n---METRIC---\nMemTotal: 2034060 kB\n---METRIC---\nuptime",
            stderr="",
        )
        gw_data = probe_ssh_node(
            node_key="GW",
            user="root",
            transports=[("lan", "192.168.8.1", 22)],
            cmd="probe_cmd",
            timeout=2.0,
        )
        assert gw_data["status"] == "ONLINE"
        assert gw_data["ram_gb"] == 2.0
        assert gw_data["metrics"]["ram_gb"]["measured"] is True
        assert gw_data["metrics"]["ram_gb"]["value"] == 2.0


class TestProbeMeshAndSchema:
    """Validate full mesh schema conformity and table formatting."""

    def test_probe_mesh_schema_keys(self):
        report = probe_mesh(timeout=2.0)
        assert "timestamp" in report
        assert "nodes" in report
        assert "summary" in report

        nodes = report["nodes"]
        expected_keys = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "GW", "L9"]
        for k in expected_keys:
            assert k in nodes, f"Missing node {k} in report"
            n = nodes[k]
            assert "status" in n
            assert "measured" in n
            assert n["status"] in ["ONLINE", "PARTIAL", "OFFLINE"]

        # Honest offline nodes
        assert nodes["L4"]["status"] == "OFFLINE"
        assert nodes["L4"]["measured"] is False
        assert nodes["L4"]["value"] is None

        assert nodes["L7"]["status"] == "OFFLINE"
        assert nodes["L7"]["measured"] is False

        assert nodes["L9"]["status"] == "OFFLINE"
        assert nodes["L9"]["measured"] is False

        # Live online nodes
        assert nodes["L1"]["status"] == "ONLINE"
        assert nodes["L1"]["measured"] is True

        assert nodes["L2"]["status"] == "ONLINE"
        assert nodes["L2"]["tb_speed_gbps"] == 20

        assert nodes["L5"]["status"] == "ONLINE"
        assert nodes["L5"]["tb_speed_gbps"] == 40

        assert nodes["L8"]["status"] == "ONLINE"
        assert nodes["L8"]["tb_speed_gbps"] == 40

        assert nodes["GW"]["status"] == "ONLINE"
        assert nodes["GW"]["model"] == "GL-BE14000"

    def test_format_table_rendering_dashes(self):
        sample_report = {
            "timestamp": "2026-10-07T03:00:00Z",
            "nodes": {
                "L1": {
                    "status": "ONLINE", "transport": "local", "endpoint": "localhost",
                    "latency_ms": 0.0, "tb_speed_gbps": None, "cpu": "Apple M4 Pro", "ram_gb": 24.0,
                    "measured": True
                },
                "L4": {
                    "status": "OFFLINE", "transport": None, "endpoint": None,
                    "latency_ms": None, "tb_speed_gbps": None, "cpu": None, "ram_gb": None,
                    "measured": False
                },
            },
            "summary": {"total": 2, "online": 1, "partial": 0, "offline": 1, "measured_count": 1},
        }
        table_output = format_table(sample_report)
        assert "L1" in table_output
        assert "Apple M4 Pro" in table_output
        assert "24.0 GB" in table_output
        assert "L4" in table_output
        # Offline node shows -- for unmeasured metrics
        assert "--" in table_output


class TestCliIntegration:
    """Validate CLI execution via subprocess."""

    def test_cli_json_invocation(self):
        script_path = REPO_ROOT / "06_scripts_and_tooling" / "network" / "verify_probes.py"
        res = subprocess.run(
            [sys.executable, str(script_path), "--json", "--timeout", "2.0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=25,
        )
        assert res.returncode == 0, f"CLI exited with error: {res.stderr}"

        data = json.loads(res.stdout)
        assert "timestamp" in data
        assert "nodes" in data
        assert "L1" in data["nodes"]
        assert data["nodes"]["L1"]["status"] == "ONLINE"
        assert data["nodes"]["L4"]["status"] == "OFFLINE"
        assert data["nodes"]["L4"]["measured"] is False

    def test_cli_output_file(self, tmp_path):
        out_file = tmp_path / "probes_test.json"
        script_path = REPO_ROOT / "06_scripts_and_tooling" / "network" / "verify_probes.py"
        res = subprocess.run(
            [sys.executable, str(script_path), "--output", str(out_file), "--timeout", "2.0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=25,
        )
        assert res.returncode == 0, f"CLI exited with error: {res.stderr}"
        assert out_file.exists()

        content = json.loads(out_file.read_text())
        assert "nodes" in content
        assert "summary" in content


class TestZeroMockCompliance:
    """Inspect source code of verify_probes.py to ensure zero forbidden fake constants."""

    def test_no_hardcoded_fake_constants(self):
        script_path = REPO_ROOT / "06_scripts_and_tooling" / "network" / "verify_probes.py"
        code = script_path.read_text()

        forbidden_patterns = [
            "82.8 GB VRAM",  # spec-ok: test pattern checking absence
            "109.0 GB RAM",  # spec-ok: test pattern checking absence
            "GL-MT3600BE",  # spec-ok: test pattern checking absence
            "rtt = 0.27",  # spec-ok: test pattern checking absence
            "1734 ELO",  # spec-ok: test pattern checking absence
            "Tankya",  # spec-ok: test pattern checking absence
            "Lintes",  # spec-ok: test pattern checking absence
        ]
        for pattern in forbidden_patterns:
            assert pattern not in code, f"Forbidden mock constant '{pattern}' found in verify_probes.py!"
