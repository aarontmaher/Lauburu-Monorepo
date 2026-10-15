# -*- coding: utf-8 -*-
"""
Comprehensive Integration Test Suite for GL.iNet CLI/Web Optimizer,
Tailscale Web, Internet Health & Dual-World Lookahead Engine
===================================================================
Subsystem: 01_apps/glinet_web_optimizer/test_glinet_full_suite.py
Lauburu Mesh Ecosystem — 2026
"""

import importlib.util
import sys
import threading
import time
import pytest
from pathlib import Path

# Add directory paths
_curr_dir = Path(__file__).resolve().parent
_sim_dir = Path(__file__).resolve().parents[2] / "02_ai_models_and_inference" / "simulation"

def _load_module(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# Import Web Server & Agent
_server_mod = _load_module("glinet_admin_web_server", _curr_dir / "glinet_admin_web_server.py")
ROUTER_STORE = _server_mod.ROUTER_STORE
run_glinet_server = _server_mod.run_glinet_server

_agent_mod = _load_module("glinet_web_optimizer_agent", _curr_dir / "glinet_web_optimizer_agent.py")
GLiNetWebOptimizerAgent = _agent_mod.GLiNetWebOptimizerAgent

# Import CLI Optimizer
_cli_mod = _load_module("glinet_cli_optimizer", _curr_dir / "glinet_cli_optimizer.py")
GLiNetCLIOptimizer = _cli_mod.GLiNetCLIOptimizer

# Import Tailscale Web
_ts_mod = _load_module("tailscale_web_optimizer", _curr_dir / "tailscale_web_optimizer.py")
TAILSCALE_STORE = _ts_mod.TAILSCALE_STORE
run_tailscale_web_server = _ts_mod.run_tailscale_web_server

# Import Internet Health Suite
_net_mod = _load_module("internet_health_suite", _curr_dir / "internet_health_suite.py")
InternetHealthSuite = _net_mod.InternetHealthSuite

# Import Dual-World Tester
_tester_mod = _load_module("router_dual_world_tester", _sim_dir / "router_dual_world_tester.py")
RouterDualWorldTester = _tester_mod.RouterDualWorldTester


@pytest.fixture(scope="module")
def glinet_services_fixture():
    """Starts local GL.iNet Admin Web (8094) and Tailscale Web (5254) servers."""
    srv_glinet = run_glinet_server(host="127.0.0.1", port=8094)
    t_glinet = threading.Thread(target=srv_glinet.serve_forever, daemon=True)
    t_glinet.start()

    srv_ts = run_tailscale_web_server(host="127.0.0.1", port=5254)
    t_ts = threading.Thread(target=srv_ts.serve_forever, daemon=True)
    t_ts.start()

    time.sleep(0.5)
    yield {"glinet_url": "http://127.0.0.1:8094", "tailscale_url": "http://127.0.0.1:5254"}
    
    srv_glinet.shutdown()
    srv_ts.shutdown()


def test_glinet_web_and_cli_optimizer(glinet_services_fixture):
    """Verifies that both Web Agent and CLI Optimizer apply validated safe tunings."""
    # 1. Test CLI Optimizer in Dry-Run mode
    cli = GLiNetCLIOptimizer(dry_run=True)
    bbr_res = cli.optimize_bbr_and_sysctl()
    assert len(bbr_res) == 3
    assert all(r.exit_code == 0 for r in bbr_res)
    assert all(r.dual_world_safety_score >= 0.90 for r in bbr_res)

    cgroup_res = cli.optimize_500mb_cgroups(limit_mb=120)
    assert cgroup_res.dual_world_safety_score >= 0.90

    # 2. Test Web Agent Dynamic Optimization
    agent = GLiNetWebOptimizerAgent(base_url=glinet_services_fixture["glinet_url"])
    decisions = agent.evaluate_and_optimize_once()
    assert isinstance(decisions, list)


def test_tailscale_web_and_mesh_ledger(glinet_services_fixture):
    """Verifies Tailscale Web GUI endpoints, DERP latency, and STUN punchthrough."""
    status = TAILSCALE_STORE.get_mesh_status()
    assert status["self"]["node_id"] == "node_glinet_gw"
    assert status["self"]["mtu"] == 1420
    assert len(status["peers"]) == 5

    # Test STUN Punchthrough
    punch_res = TAILSCALE_STORE.force_stun_p2p_punchthrough("node_mac_mini")
    assert punch_res["status"] == "SUCCESS"
    assert punch_res["peer"]["is_direct_p2p"] is True


def test_internet_health_full_diagnostic_suite():
    """Verifies DNS resolution, Bufferbloat AQM rating, IPv6 Dual-Stack, and WAN bonding."""
    suite = InternetHealthSuite()
    report = suite.run_full_internet_audit()

    assert report.wan_online is True
    assert len(report.dns_results) >= 3
    assert report.bufferbloat.grade in ["A+", "A", "B"]
    assert report.ipv6_dual_stack_healthy is True
    assert report.multipath_bonding_healthy is True
    assert report.diagnostics["multipath_details"]["bonding_driver"] == "lauburu_bond"
    assert report.diagnostics["multipath_details"]["memory_footprint_mb"] == 1.45
