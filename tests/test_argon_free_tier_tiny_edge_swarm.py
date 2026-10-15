#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & E2E Verification Suite for:
1. Gemini 4 Argon vs. Flash 1.0x Token Cost Parity
2. Live Device Telemetry & Overload Guard (Darwin Mach vm_stat / sysctl)
3. Tiny & Edge Local Model Limiter (<=8B normal, <=2B under RAM pressure; >8B blocked)
4. Large-Scale Homogeneous Same-Model Swarm ROI Ranking
5. P0 Sellable Apps Completion & Verification Swarm
Strict Rule #0 / Rule #1 Compliance: Zero mocks, authentic OS telemetry & real build artifacts.
"""

import json
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
for p in [REPO_ROOT, REPO_ROOT / "05_agents_and_swarms", REPO_ROOT / "06_scripts_and_tooling"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from model_cost_governor import (
    ALLOWED_TINY_AND_EDGE_LOCAL_MODELS,
    ARGON_FLASH_TOKEN_PARITY_MODELS,
    BLOCKED_HEAVY_LOCAL_MODELS,
    get_host_ram_telemetry,
    validate_model,
    verify_argon_flash_cost_parity,
)
from cloud_ai_routing_governor import CloudAIRoutingGovernor
from priority_work_governor import PriorityWorkGovernor
from argon_free_tier_tiny_edge_swarm import (
    ArgonFreeTierTinyEdgeSwarm,
    OBSIDIAN_REPORT_FILE,
    TELEMETRY_STATE_FILE,
)


def test_argon_flash_token_parity_verification():
    """Verify Gemini 4 Argon High/Medium/Low have 1.0x token cost parity with Gemini 3.8 Flash."""
    for model_id in [
        "gemini-4-argon-high",
        "gemini-4-argon-medium",
        "gemini-4-argon-low",
        "gemini-3.8-flash-high",
        "gemini-3.8-flash-medium",
        "gemini-3.8-flash-low",
    ]:
        res = verify_argon_flash_cost_parity(model_id)
        assert res["token_cost_ratio"] == 1.0
        assert res["parity_confirmed"] is True
        assert res["use_g1_credits"] is True

    with pytest.raises(ValueError, match="Unknown parity model"):
        verify_argon_flash_cost_parity("non-existent-model-xyz")


def test_live_transcript_and_cli_token_parity_telemetry():
    """Verify live brain transcript scanning and Antigravity CLI settings parity check."""
    swarm = ArgonFreeTierTinyEdgeSwarm()
    parity = swarm.verify_live_argon_flash_token_parity()
    assert parity["argon_to_flash_token_cost_ratio"] == 1.0
    assert parity["parity_confirmed"] is True
    assert parity["use_g1_credits"] is True
    assert parity["live_transcript_telemetry"]["total_transcripts_on_disk"] > 0
    assert parity["live_transcript_telemetry"]["recent_transcripts_sampled"] > 0
    assert parity["live_transcript_telemetry"]["steps_inspected"] > 0


def test_tiny_and_edge_local_model_limiter_and_overload_boundaries():
    """
    Test boundary conditions for validate_model:
    - Empty/blank strings rejected
    - Paid models rejected
    - Heavy local models (>8B) rejected
    - High RAM pressure (>80% / <4.8GB free) caps local models at <=2.0B
    - Normal RAM sanctuary (<=80% and >=4.8GB free) allows Edge models up to 8.0B
    """
    # 1. Empty or whitespace model names
    with pytest.raises(ValueError, match="Empty model_name"):
        validate_model("")
    with pytest.raises(ValueError, match="Empty model_name"):
        validate_model("   ")

    # 2. Paid models blocked
    for paid in ["gemini-3.1-pro", "gpt-4o", "claude-3-5-sonnet", "o1-preview"]:
        with pytest.raises(ValueError, match="BLOCKED"):
            validate_model(paid)

    # 3. Heavy local models (>8B) blocked
    for heavy in BLOCKED_HEAVY_LOCAL_MODELS:
        with pytest.raises(ValueError, match="BLOCKED HEAVY LOCAL MODEL"):
            validate_model(heavy)

    # 4. Boundary: High RAM pressure state (88.5% used, 2.76 GB free -> cap = 2.0B)
    overloaded_ram = {
        "total_gb": 24.0,
        "used_gb": 21.24,
        "free_headroom_gb": 2.76,
        "utilization_pct": 88.5,
        "pressure_level": 2,
        "is_overloaded": True,
        "max_allowed_local_params_b": 2.0,
    }
    # Tiny/Edge <= 2.0B must pass under overload
    assert validate_model("lauburu-lens-argon:latest", host_telemetry=overloaded_ram) is True
    assert validate_model("SmolLM2-135M-Instruct", host_telemetry=overloaded_ram) is True
    assert validate_model("Qwen2.5-Coder-1.5B-Instruct", host_telemetry=overloaded_ram) is True
    assert validate_model("Custom-Tiny-500M-Local", host_telemetry=overloaded_ram) is True
    # Argon & Free-Tier Cloud models (0 local RAM) must pass under overload
    assert validate_model("gemini-4-argon-high", host_telemetry=overloaded_ram) is True
    assert validate_model("deepseek-ai/deepseek-v4-flash", host_telemetry=overloaded_ram) is True

    # 7B and 8B local models (including localhost port endpoints and unlisted 3B-8B models) must be blocked when overloaded
    for edge_over_2b in [
        "Qwen2.5-Coder-7B-Instruct-Q4_K_M",
        "Hermes-3-Llama-3.1-8B-Q4_K_M",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:8090",
        "Phi-3-Mini-3.8B-Instruct",
    ]:
        with pytest.raises(ValueError, match="DEVICE OVERLOAD GUARD"):
            validate_model(edge_over_2b, host_telemetry=overloaded_ram)

    # Unlisted heavy local models (>8B) and unverified local model strings must be blocked even in healthy RAM state
    healthy_ram = {
        "total_gb": 24.0,
        "used_gb": 16.8,
        "free_headroom_gb": 7.2,
        "utilization_pct": 70.0,
        "pressure_level": 1,
        "is_overloaded": False,
        "max_allowed_local_params_b": 8.0,
    }
    for unlisted_heavy in [
        "Qwen2.5-14B-Instruct",
        "Mistral-24B-Local-GGUF",
        "Llama-3.1-70B-Instruct",
        "http://127.0.0.1:8082",
        "http://127.0.0.1:8083",
    ]:
        with pytest.raises(ValueError, match="BLOCKED HEAVY LOCAL MODEL"):
            validate_model(unlisted_heavy, host_telemetry=healthy_ram)

    with pytest.raises(ValueError, match="BLOCKED UNVERIFIED LOCAL MODEL"):
        validate_model("mystery-local-weights-v1", host_telemetry=healthy_ram)

    # 5. Boundary: Normal RAM sanctuary state (70% used, 7.2 GB free -> cap = 8.0B)
    assert validate_model("Qwen2.5-Coder-7B-Instruct-Q4_K_M", host_telemetry=healthy_ram) is True
    assert validate_model("Hermes-3-Llama-3.1-8B-Q4_K_M", host_telemetry=healthy_ram) is True
    assert validate_model("http://127.0.0.1:8081", host_telemetry=healthy_ram) is True
    assert validate_model("http://127.0.0.1:8090", host_telemetry=healthy_ram) is True


def test_live_device_telemetry_monitoring():
    """Verify authentic Darwin Mach vm_stat & sysctl telemetry structure and overload policy."""
    swarm = ArgonFreeTierTinyEdgeSwarm()
    dev = swarm.monitor_live_device_telemetry()
    ram = dev["ram_telemetry"]
    assert ram["total_gb"] >= 16.0
    assert 0.0 < ram["utilization_pct"] <= 100.0
    assert dev["max_allowed_local_params_b"] in (2.0, 8.0)
    assert len(dev["eligible_tiny_edge_local_models"]) >= 8
    for m in dev["eligible_tiny_edge_local_models"]:
        assert m["params_b"] <= dev["max_allowed_local_params_b"]


def test_large_scale_same_model_swarm_roi_ranking():
    """Verify Large-Scale Homogeneous Same-Model Swarms are unified and ranked by ROI with P0 Sellable Apps #1."""
    swarm = ArgonFreeTierTinyEdgeSwarm()
    gov = CloudAIRoutingGovernor()
    ranked = swarm.identify_high_roi_same_model_swarms()
    gov_ranked = gov.get_high_roi_same_model_swarms()
    assert ranked == gov_ranked
    assert len(ranked) == 7
    scores = [r["roi_score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)

    for rule in ranked:
        tier_key = rule["tier_key"]
        assert tier_key in gov.tiers
        assert gov.tiers[tier_key]["model_id"] == rule["homogeneous_model"]

    top = ranked[0]
    assert top["swarm_id"] == "SWARM_SAME_MODEL_01_ARGON_HIGH_16X"
    assert top["homogeneous_model"] == "gemini-4-argon-high"
    assert top["parallel_replicas"] == 16
    assert top["token_cost_vs_flash"] == 1.0
    assert "Sellable Apps" in top["target_task"]


def test_cloud_ai_routing_governor_argon_and_tiny_edge_routes():
    """Verify CloudAIRoutingGovernor routes P0 sellable apps to Argon High and tiny_edge_local to 0.5B."""
    gov = CloudAIRoutingGovernor()
    r_p0 = gov.route_task("sellable_apps_p0", complexity="high", estimated_tokens=4000)
    assert r_p0["chosen_target"] == "gemini_4_argon_high"
    assert r_p0["model_id"] == "gemini-4-argon-high"
    assert r_p0["token_cost_multiplier_vs_flash"] == 1.0
    assert r_p0["cost_usd"] == 0.00

    r_tiny = gov.route_task("tiny_edge_local", complexity="low", estimated_tokens=400)
    assert r_tiny["chosen_target"] == "local_tiny_edge_argon_companion"
    assert r_tiny["model_id"] == "lauburu-lens-argon:latest"

    r_smol = gov.route_task("telemetry_anomaly_filter", complexity="low", estimated_tokens=200)
    assert r_smol["chosen_target"] == "local_tiny_smollm2"
    assert r_smol["model_id"] == "SmolLM2-135M-Instruct"


def test_concurrent_16x_swarm_atomic_state_locking():
    """Verify 16x concurrent worker threads/processes increment CloudAIRoutingGovernor usage atomically without race loss."""
    import concurrent.futures

    gov = CloudAIRoutingGovernor()
    before_count = gov._load_state()["daily_usage"].get("gemini_4_argon_high", 0)

    def _worker(_idx: int):
        g = CloudAIRoutingGovernor()
        return g.route_task("sellable_apps_p0", complexity="high", estimated_tokens=2000)

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(_worker, range(16)))

    assert len(results) == 16
    after_count = CloudAIRoutingGovernor()._load_state()["daily_usage"]["gemini_4_argon_high"]
    assert after_count == before_count + 16


def test_priority_work_governor_p0_sellable_apps_first():
    """Verify PriorityWorkGovernor places P00 first and purges heavy 80B/27B local models from all priorities."""
    pgov = PriorityWorkGovernor()
    priorities = pgov.state["priorities"]
    assert priorities[0]["id"] == "P00"
    assert "Sellable Apps" in priorities[0]["title"]
    assert "Gemini 4 Argon High" in priorities[0]["assigned_model"]
    assert priorities[1]["id"] == "P00B"

    for p in priorities:
        assert "Qwen MoE 80B" not in p["assigned_model"]
        assert "Qwen MoE 80B" not in p["review_model"]
        assert "Qwen 3.8 Max" not in p["assigned_model"]
        assert "Qwen 3.8 Max" not in p["review_model"]


def test_execute_sellable_apps_p0_swarm_end_to_end():
    """Verify full E2E execution of the Argon + Free-Tier Cloud + Tiny/Edge Swarm for P0 Sellable Apps."""
    swarm = ArgonFreeTierTinyEdgeSwarm()
    report = swarm.execute_sellable_apps_p0_swarm()

    portfolio = report["sellable_apps_p0_portfolio"]
    assert portfolio["priority_level"] == "P0_HIGHEST_PRIORITY"
    assert portfolio["total_sellable_apps_verified"] == 5
    assert portfolio["all_sellable_apps_ship_ready"] is True

    app_ids = {a["app_id"] for a in portfolio["applications"]}
    assert app_ids == {"combat_lab", "openvitals", "screen_lens", "cable_analyzer", "showrunner"}

    for app in portfolio["applications"]:
        assert app["source_verified"] is True
        assert app["source_file_count"] > 0
        assert app["build_artifact_count"] > 0
        assert app["gross_margin_pct"] >= 85.0
        assert app["sellable_status"] == "SHIP_READY_VERIFIED"

    assert TELEMETRY_STATE_FILE.is_file()
    persisted = json.loads(TELEMETRY_STATE_FILE.read_text(encoding="utf-8"))
    assert persisted["argon_flash_token_parity"]["parity_confirmed"] is True
    assert OBSIDIAN_REPORT_FILE.is_file()
    assert "SWARM_SAME_MODEL_01_ARGON_HIGH_16X" in OBSIDIAN_REPORT_FILE.read_text(encoding="utf-8")


def test_binary_argon_flash_parity_and_budget_proxy_zero_cost():
    """Verify binary-level Argon/Flash symbol proof and AI Gateway budget_proxy $0.00 parity."""
    from model_cost_governor import inspect_antigravity_binary_and_settings, FREE_CLOUD_API_MODELS, ZERO_COST_MODEL_LADDER
    from ai_gateway.budget_proxy import is_free_tier, estimate_cost

    proof = inspect_antigravity_binary_and_settings()
    assert proof["language_server_exists"] is True
    assert proof["all_binary_model_symbols_present"] is True
    assert proof["g1_credit_governance_present"] is True
    for sym in [
        "Gemini 4 Argon (High)",
        "gemini-4-argon",
        "gemini-4-argon-high",
        "gemini-4-argon-medium",
        "gemini-4-argon-low",
        "Gemini 3.8 Flash (High)",
        "gemini-3.8-flash-high",
        "gemini-3.8-flash-medium",
        "gemini-3.8-flash-low",
    ]:
        assert proof["binary_model_symbols_verified"][sym] is True

    # Verify budget_proxy treats Argon and Flash 3.8 at $0.00 (1.0x G1 parity) instead of $5/$20 default
    for model_name in [
        "gemini-4-argon",
        "gemini-4-argon-high",
        "gemini-4-argon-medium",
        "gemini-4-argon-low",
        "gemini-3.8-flash",
        "gemini-3.8-flash-high",
        "gemini-3.8-flash-medium",
        "gemini-3.8-flash-low",
    ]:
        assert is_free_tier("google", model_name) is True
        assert estimate_cost(model_name, 100_000, 50_000, is_free=False) == 0.0
        assert estimate_cost(model_name, 100_000, 50_000, is_free=True) == 0.0

    # Verify real local Tiny/Edge ports (8089, 8087, 8085) and Groq in governor
    for ep in ["http://127.0.0.1:8089", "http://127.0.0.1:8087", "http://127.0.0.1:8085"]:
        assert ep in ALLOWED_TINY_AND_EDGE_LOCAL_MODELS
        assert ep in ZERO_COST_MODEL_LADDER
    assert "llama-3.3-70b-versatile" in FREE_CLOUD_API_MODELS
    assert "grok-2-latest" in FREE_CLOUD_API_MODELS


def test_peripheral_node_overload_and_local_tiny_edge_endpoints():
    """Verify live peripheral Glances overload detection and Tiny/Edge port telemetry."""
    swarm = ArgonFreeTierTinyEdgeSwarm()
    dev = swarm.monitor_live_device_telemetry()
    eps = {e["port"]: e for e in dev["live_local_tiny_edge_endpoints"]}
    assert {8089, 8087, 8085}.issubset(set(eps.keys()))
    assert eps[8089]["live"] is True
    assert eps[8087]["live"] is True
    assert eps[8085]["live"] is True

    p_nodes = {n["node_id"]: n for n in dev["peripheral_node_telemetry"]}
    assert "L8_lauburu" in p_nodes
    assert "L1a_mac_air_m4" in p_nodes
    l1a = p_nodes["L1a_mac_air_m4"]
    if l1a.get("reachable"):
        expected_overload = (
            l1a["ram_used_pct"] > 80.0
            or l1a["disk_used_pct"] >= 95.0
            or l1a["disk_free_gb"] < 5.0
        )
        assert l1a["is_overloaded"] is expected_overload
        if expected_overload:
            assert "L1a_mac_air_m4" in dev["excluded_overloaded_peripheral_nodes"]
            assert "L1a_mac_air_m4" not in dev["eligible_offload_peripheral_nodes"]
        else:
            assert "L1a_mac_air_m4" in dev["eligible_offload_peripheral_nodes"]
            assert "L1a_mac_air_m4" not in dev["excluded_overloaded_peripheral_nodes"]


def test_master_free_tier_ai_maximizer_fixes():
    """Verify master_free_tier_ai_maximizer loads ~/.env, uses Darwin vm_stat without find/rm, and uses grok-2-latest + groq_ai."""
    import inspect
    import master_free_tier_ai_maximizer as maximizer

    src_sanctuary = inspect.getsource(maximizer.check_host_ram_sanctuary)
    assert "__pycache__" not in src_sanctuary
    assert "get_host_ram_telemetry" in src_sanctuary
    assert maximizer.check_host_ram_sanctuary() is True

    src_grok = inspect.getsource(maximizer.call_xai_grok)
    assert "grok-4.20-0309-non-reasoning" not in src_grok
    assert "grok-2-latest" in src_grok

    src_harvest = inspect.getsource(maximizer.execute_api_harvest_cycle)
    assert "grok-4.20-0309-non-reasoning" not in src_harvest
    assert "grok-2-latest" in src_harvest
    assert "groq_ai" in src_harvest
    assert "groq_ai" in maximizer.DAILY_QUOTAS

    src_groq = inspect.getsource(maximizer.call_groq)
    assert "llama-3.3-70b-versatile" in src_groq

    src_cf = inspect.getsource(maximizer.call_cloudflare_ai)
    assert "CLOUDFLARE_ACCOUNT_ID" in src_cf


def test_prima_daemon_authentic_attribution_and_hot_failover_8089_to_8085():
    """
    Verify decentralized_prima_daemon (:8082):
    1. Excludes overloaded L1a (100.121.202.34) from candidate_endpoints (and in mesh_multiport_bridge.py)
    2. Routes default requests to :8089 with authentic model name qwen2.5-0.5b-instruct-q4_k_m.gguf (not llama_4_scout_109b)
    3. Seamlessly hot-fails over to :8085 (Hermes-3-Llama-3.1-8B.Q4_K_M.gguf) when :8089 is unavailable/skipped
    """
    import urllib.request

    prima_src = (REPO_ROOT / "02_ai_models_and_inference" / "decentralized_prima_daemon.py").read_text(encoding="utf-8")
    bridge_src = (REPO_ROOT / "02_ai_models_and_inference" / "mesh_multiport_bridge.py").read_text(encoding="utf-8")
    assert "100.121.202.34" not in prima_src
    assert "100.121.202.34" not in bridge_src
    assert "llama_4_scout_109b" not in prima_src

    # 1. Primary route (:8082 -> :8089 Qwen2.5-0.5B)
    payload_primary = json.dumps({
        "model": "ai",
        "messages": [{"role": "user", "content": "Reply with OK"}],
        "max_tokens": 8,
        "temperature": 0.0,
    }).encode("utf-8")
    req_primary = urllib.request.Request(
        "http://127.0.0.1:8082/v1/chat/completions",
        data=payload_primary,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_primary, timeout=15.0) as r1:
        data1 = json.loads(r1.read().decode("utf-8"))
    assert data1["model"] == "qwen2.5-0.5b-instruct-q4_k_m.gguf"
    assert data1["routed_endpoint"] == "http://127.0.0.1:8089/v1/chat/completions"
    assert len(data1["choices"][0]["message"]["content"].strip()) > 0

    # 2. Hot-failover route (:8082 with :8089 skipped -> fails over to :8085 Hermes-3-8B)
    req_failover = urllib.request.Request(
        "http://127.0.0.1:8082/v1/chat/completions",
        data=payload_primary,
        headers={"Content-Type": "application/json", "X-Prima-Skip-Port": "8089"},
    )
    with urllib.request.urlopen(req_failover, timeout=25.0) as r2:
        data2 = json.loads(r2.read().decode("utf-8"))
    assert data2["model"] == "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"
    assert data2["routed_endpoint"] == "http://127.0.0.1:8085/v1/chat/completions"
    assert len(data2["choices"][0]["message"]["content"].strip()) > 0


def test_all_8_flagship_apps_100_percent_production_ready():
    """Verify all 8 flagship commercial apps achieve 100.0% PRODUCTION_READY with live Tiny/Edge local AI."""
    swarm = ArgonFreeTierTinyEdgeSwarm()
    report = swarm.execute_sellable_apps_p0_swarm()
    f8 = report["sellable_apps_p0_portfolio"]["flagship_8_apps_readiness"]
    assert f8["total_apps"] == 8
    assert f8["production_ready_count"] == 8
    assert f8["all_8_production_ready"] is True
    for app in f8["apps"]:
        assert app["total_readiness"] == 100.0
        assert app["readiness_status"] == "PRODUCTION_READY"
        assert app["ai_integration_status"] == "INTEGRATED (LOCAL)"


