# -*- coding: utf-8 -*-
"""
Verification Tests for Containerized GL.iNet Web GUI & Dynamic AI Optimizer
===========================================================================
Subsystem: 01_apps/glinet_web_optimizer/test_glinet_web_optimizer.py
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

# Import server
_server_mod = _load_module("glinet_admin_web_server", _curr_dir / "glinet_admin_web_server.py")
ROUTER_STORE = _server_mod.ROUTER_STORE
run_glinet_server = _server_mod.run_glinet_server

# Import agent
_agent_mod = _load_module("glinet_web_optimizer_agent", _curr_dir / "glinet_web_optimizer_agent.py")
GLiNetWebOptimizerAgent = _agent_mod.GLiNetWebOptimizerAgent

# Import dual world tester
_tester_mod = _load_module("router_dual_world_tester", _sim_dir / "router_dual_world_tester.py")
RouterDualWorldTester = _tester_mod.RouterDualWorldTester


@pytest.fixture(scope="module")
def web_server_fixture():
    """Starts local GL.iNet Admin Web Server on port 8092 for testing."""
    server = run_glinet_server(host="127.0.0.1", port=8092)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    yield "http://127.0.0.1:8092"
    server.shutdown()


def test_glinet_web_server_status(web_server_fixture):
    """Verifies that the GL.iNet Admin Web Server exposes authentic 500MB router telemetry."""
    agent = GLiNetWebOptimizerAgent(base_url=web_server_fixture)
    status = agent.fetch_router_status()
    assert status is not None
    assert status["system"]["memory_total_kb"] == 503808  # 492 MB
    assert status["system"]["model"] == "GL.iNet GL-MT3600BE"
    assert status["network"]["wan_mtu"] == 1500


def test_dual_world_lookahead_validation():
    """Verifies that RouterDualWorldTester accurately validates candidate trajectories."""
    tester = RouterDualWorldTester()
    
    # 1. Valid safe trajectory
    res_safe = tester.evaluate_healing_trajectory(
        action_name="restart_tailscale",
        parameters={"rss_mb": 1.5},
        lookahead_steps=10,
    )
    assert res_safe.is_safe is True
    assert res_safe.agentworld_safety_score >= 0.90
    assert res_safe.webworld_layout_overflows == 0
    assert res_safe.recommended_action == "APPLY"

    # 2. Cgroup memory rebalance
    res_cgroup = tester.evaluate_healing_trajectory(
        action_name="cgroup_memory_rebalance",
        parameters={"cap_mb": 120},
        lookahead_steps=15,
    )
    assert res_cgroup.is_safe is True
    assert res_cgroup.agentworld_safety_score >= 0.90


def test_dynamic_web_optimizer_cycle(web_server_fixture):
    """Verifies that the AI Web Optimizer dynamically tunes Wi-Fi and 500MB cgroups via ubus."""
    # Reset store to sub-optimal state
    ROUTER_STORE.state["network"]["wifi_airtime_congestion_pct"] = 35.0
    ROUTER_STORE.state["network"]["wifi_5g_channel"] = 36
    ROUTER_STORE.state["cgroups"]["ai_memory_max_bytes"] = 400 * 1024 * 1024  # 400MB (excessive for 500MB RAM)

    agent = GLiNetWebOptimizerAgent(base_url=web_server_fixture)
    decisions = agent.evaluate_and_optimize_once()

    assert len(decisions) >= 2
    # Verify Wi-Fi channel was rebalanced
    wifi_dec = next((d for d in decisions if d.parameter_name == "wifi_5g_channel"), None)
    assert wifi_dec is not None
    assert wifi_dec.applied is True
    assert wifi_dec.proposed_value == 149

    # Verify 500MB Cgroup RAM safety ceiling was enforced
    cgroup_dec = next((d for d in decisions if d.parameter_name == "ai_memory_max_bytes"), None)
    assert cgroup_dec is not None
    assert cgroup_dec.applied is True
    assert cgroup_dec.proposed_value == 125829120  # 120 MB cap

    # Verify updated server state
    new_status = agent.fetch_router_status()
    assert new_status["network"]["wifi_5g_channel"] == 149
    assert new_status["cgroups"]["ai_memory_max_bytes"] == 125829120
