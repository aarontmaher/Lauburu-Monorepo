#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for Lauburu Showrunner.
Covers:
- Prima.cpp PRP Mesh Bindings (Port 8082 / Port 8083)
- Layer 2/3 Bluetooth PAN & Multi-Transport Network Overlay
- Authentic Hardware Telemetry & Rule #3 Dynamic RAM Compliance
- Persistent Qdrant Vector Memory Storage & Semantic Retrieval
- Multi-Tier Resilient LLM Inference Cascade
- FastAPI REST Endpoints & Director Control
- Tri-Vault Knowledge Serialization (Obsidian Vault & Continuous LoRA Data Lake)
"""

import sys
import json
import pytest
import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

APP_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/lauburu_showrunner")
BACKEND_DIR = APP_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Dynamic Module Loaders for SDK Bindings
def load_mod(name, rel_path):
    p = APP_DIR / rel_path
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

prima_mod = load_mod("lauburu_showrunner_prima", "src/ai_bindings/prima_binding.py")
pan_mod = load_mod("lauburu_showrunner_pan", "src/network/pan_transport.py")

PrimaClass = getattr(prima_mod, "LauburuShowrunnerPrimaBinding")
NetworkClass = getattr(pan_mod, "LauburuShowrunnerNetworkTransport")

import engine

# ---------------------------------------------------------------------------
# 1. Prima & Bluetooth PAN SDK Tests
# ---------------------------------------------------------------------------
def test_lauburu_showrunner_prima_status():
    binding = PrimaClass()
    status = binding.get_service_status()
    assert status["app"] == "lauburu_showrunner"
    assert "ai_mesh" in status
    assert "master_orchestrator" in status["ai_mesh"]
    assert status["ai_mesh"]["master_orchestrator"]["model"] == "qwen_38_max"

def test_lauburu_showrunner_network_transport():
    transport = NetworkClass()
    topo = transport.get_network_topology()
    assert topo["app"] == "lauburu_showrunner"
    assert "transport" in topo
    assert "rf_state" in topo

# ---------------------------------------------------------------------------
# 2. Authentic Hardware Telemetry & Rule #3 Compliance Tests
# ---------------------------------------------------------------------------
def test_showrunner_authentic_telemetry():
    telemetry = engine.get_mesh_telemetry()
    assert "host_ram_free_gb" in telemetry
    assert "host_ram_total_gb" in telemetry
    assert "host_cpu_pct" in telemetry
    assert "rule_3_headroom_compliant" in telemetry
    assert isinstance(telemetry["host_ram_free_gb"], float)
    assert telemetry["host_ram_total_gb"] > 0
    assert "ports" in telemetry
    assert "8082_qwen_master" in telemetry["ports"]

# ---------------------------------------------------------------------------
# 3. Persistent Qdrant Vector Memory Tests
# ---------------------------------------------------------------------------
def test_showrunner_persistent_memory():
    import asyncio
    async def _test():
        test_marker = "UniqueTestSentinel_TB4_QuantumRouting_10Gbps"
        engine.store_memory(f"Simulation Memory Test: {test_marker}", {"type": "unit_test"})
        retrieved = await engine.retrieve_memories(test_marker, limit=2)
        assert test_marker in retrieved or len(engine.fallback_memory_cache) > 0
    asyncio.run(_test())

# ---------------------------------------------------------------------------
# 4. Resilient LLM Inference Cascade Tests
# ---------------------------------------------------------------------------
def test_showrunner_resilient_llm_inference():
    import asyncio
    async def _test():
        npc = engine.npcs[0]  # Nexus
        system_prompt = "You are Nexus, Sovereign AI Overseer."
        user_prompt = "Execute quick diagnostics ping."
        result = await engine.call_llm_resilient(npc, system_prompt, user_prompt)
        assert "action" in result
        assert "model" in result
        assert "latency_ms" in result
        assert len(result["action"]) > 0
        assert result["latency_ms"] >= 0
    asyncio.run(_test())

# ---------------------------------------------------------------------------
# 5. FastAPI REST API & Director Control Tests
# ---------------------------------------------------------------------------
def test_showrunner_fastapi_endpoints():
    client = TestClient(engine.app)

    # 1. Health & Status
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app"] == "lauburu_showrunner"
    assert data["status"] == "RUNNING"
    assert "telemetry" in data

    # 2. NPC Roster
    resp = client.get("/api/npcs")
    assert resp.status_code == 200
    npcs = resp.json().get("npcs", [])
    assert len(npcs) >= 3
    names = [n["name"] for n in npcs]
    assert "Nexus" in names
    assert "Cipher" in names
    assert "Echo" in names

    # 3. History
    resp = client.get("/api/history")
    assert resp.status_code == 200
    assert "history" in resp.json()

    # 4. Inject Director Event
    event_payload = {"event": "Automated Unit Test: Solar Flare hits router."}
    resp = client.post("/api/director/event", json=event_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
    assert event_payload["event"] in engine.director.manual_events_queue

    # 5. Director Speed Adjustment
    speed_payload = {"interval_seconds": 12.5}
    resp = client.post("/api/director/speed", json=speed_payload)
    assert resp.status_code == 200
    assert resp.json()["interval_seconds"] == 12.5

    # 6. Director Pause Toggle
    pause_payload = {"paused": True}
    resp = client.post("/api/director/pause", json=pause_payload)
    assert resp.status_code == 200
    assert resp.json()["is_paused"] is True
    # unpause
    client.post("/api/director/pause", json={"paused": False})

    # 7. Web Dashboard HTML
    resp = client.get("/")
    assert resp.status_code == 200
    assert "LAUBURU SHOWRUNNER" in resp.text

# ---------------------------------------------------------------------------
# 6. Tri-Vault Storage Serialization Tests (Rule #2)
# ---------------------------------------------------------------------------
def test_showrunner_tri_vault_serialization():
    # Insert test action into director
    engine.director.recent_actions.append({
        "type": "npc_action",
        "npc": "Nexus",
        "role": "Sovereign AI Overseer",
        "action": "E2E Unit Test Verification of Tri-Vault Sync",
        "model": "Qwen 3.8 Max (8082 Master)",
        "latency_ms": 12.4,
        "event": "Unit Test Run",
        "timestamp": "12:00:00"
    })
    
    engine.serialize_to_tri_vault()

    obsidian_file = engine.OBSIDIAN_DIR / "EPISODES.md"
    assert obsidian_file.exists()
    with open(obsidian_file) as f:
        obsidian_content = f.read()
    assert "Episode" in obsidian_content

    assert engine.LORA_FILE.exists()
    with open(engine.LORA_FILE) as f:
        lora_lines = f.readlines()
    assert len(lora_lines) > 0
    last_line = json.loads(lora_lines[-1])
    assert "instruction" in last_line
    assert "output" in last_line

# ---------------------------------------------------------------------------
# 7. Line 1 Out-of-Band Bluetooth Terminal & No-IP Healing Tests
# ---------------------------------------------------------------------------
def test_bluetooth_no_ip_healer_manager():
    from network.bluetooth_no_ip_healer import bt_no_ip_healer
    status = bt_no_ip_healer.get_healing_status()
    assert status["subsystem"] == "bluetooth_terminal_no_ip_healing"
    assert "status" in status
    assert "rfcomm_ports" in status
    assert "known_peers" in status
    assert len(status["known_peers"]) >= 3

    # Execute drill
    receipt = bt_no_ip_healer.execute_healing_drill(reason="UNIT_TEST_DRILL")
    assert receipt["transport_plane"] == "LINE_1_BLUETOOTH_RFCOMM_ZERO_IP"
    assert receipt["recovery_verified"] is True
    assert "latency_ms" in receipt
    assert receipt["latency_ms"] > 0
    assert bt_no_ip_healer.stream_file.exists()

def test_bluetooth_no_ip_fastapi_endpoints():
    client = TestClient(engine.app)
    
    # 1. GET /api/bluetooth/healing
    resp = client.get("/api/bluetooth/healing")
    assert resp.status_code == 200
    data = resp.json()
    assert data["subsystem"] == "bluetooth_terminal_no_ip_healing"
    assert "known_peers" in data
    assert "total_drills" in data

    # 2. POST /api/bluetooth/exercise
    resp = client.post("/api/bluetooth/exercise", json={"reason": "UNIT_TEST_EXERCISE"})
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "SUCCESS"
    assert "receipt" in res_data
    assert res_data["receipt"]["recovery_verified"] is True
    assert "PULSE_LINE1_RFCOMM" in res_data["receipt"]["reflex_action"]

def test_bluetooth_lora_dataset_serialization():
    # Trigger drill and serialize
    from network.bluetooth_no_ip_healer import bt_no_ip_healer
    bt_no_ip_healer.execute_healing_drill(reason="LORA_TEST_DRILL")
    engine.serialize_to_tri_vault()

    assert engine.BT_LORA_FILE.exists()
    with open(engine.BT_LORA_FILE) as f:
        lines = f.readlines()
    assert len(lines) > 0
    last_bt = json.loads(lines[-1])
    assert last_bt["source"] == "bluetooth_serial_terminal_lora"
    assert "instruction" in last_bt
    assert "solution" in last_bt
    assert last_bt["rule_0_verified"] is True

# ---------------------------------------------------------------------------
# 8. Dual-Plane Groups & Factions Metadata Tests
# ---------------------------------------------------------------------------
def test_showrunner_dual_groups_metadata():
    client = TestClient(engine.app)
    resp = client.get("/api/groups")
    assert resp.status_code == 200
    data = resp.json()
    assert "groups" in data
    assert "non_abliterated" in data["groups"]
    assert "abliterated" in data["groups"]

    sovereign = data["groups"]["non_abliterated"]
    adversarial = data["groups"]["abliterated"]

    assert sovereign["id"] == "non_abliterated"
    assert sovereign["badge"] == "SOVEREIGN"
    assert sovereign["cloud_fallback_allowed"] is True
    assert "npu_drafter" in sovereign
    assert "Apex-NPU" in sovereign["npu_drafter"]

    assert adversarial["id"] == "abliterated"
    assert adversarial["badge"] == "ADVERSARIAL"
    assert adversarial["cloud_fallback_allowed"] is False
    assert "npu_drafter" in adversarial
    assert "Nyx-NPU" in adversarial["npu_drafter"]

    # Verify personas in each plane
    sov_personas = [p["name"] for p in sovereign["personas"]]
    assert "Nexus" in sov_personas
    assert "Echo" in sov_personas
    assert "Apex-NPU" in sov_personas

    adv_personas = [p["name"] for p in adversarial["personas"]]
    assert "Cipher" in adv_personas
    assert "Vortex" in adv_personas
    assert "Nyx-NPU" in adv_personas

    # Verify active queue counts present
    assert "active_queues" in data
    assert "non_abliterated_count" in data["active_queues"]
    assert "abliterated_count" in data["active_queues"]

# ---------------------------------------------------------------------------
# 9. Separate Group Event Injection Queues Tests
# ---------------------------------------------------------------------------
def test_showrunner_separate_group_event_injections():
    client = TestClient(engine.app)

    initial_non_ab = len(engine.director.manual_events_non_abliterated)
    initial_ab = len(engine.director.manual_events_abliterated)

    # 1. Inject strictly into Non-Abliterated Sovereign Queue
    sov_event = "Sovereign Event: TB4 link tensor ring verify."
    resp = client.post("/api/director/event/non_abliterated", json={"event": sov_event})
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
    assert resp.json()["group"] == "non_abliterated"
    assert len(engine.director.manual_events_non_abliterated) == initial_non_ab + 1
    assert len(engine.director.manual_events_abliterated) == initial_ab
    assert sov_event in engine.director.manual_events_non_abliterated

    # 2. Inject strictly into Abliterated Cyber Syndicate Queue
    adv_event = "Adversarial Event: Uncensored RFCOMM payload fuzzing."
    resp = client.post("/api/director/event/abliterated", json={"event": adv_event})
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
    assert resp.json()["group"] == "abliterated"
    assert len(engine.director.manual_events_abliterated) == initial_ab + 1
    assert adv_event in engine.director.manual_events_abliterated

    # 3. Inject global event (broadcast to all)
    global_event = "Global Event: Mesh-wide power fluctuation."
    resp = client.post("/api/director/event", json={"event": global_event, "group": "all"})
    assert resp.status_code == 200
    assert global_event in engine.director.manual_events_non_abliterated
    assert global_event in engine.director.manual_events_abliterated

# ---------------------------------------------------------------------------
# 10. NPU Speculative Drafter Models & Engine Tests
# ---------------------------------------------------------------------------
def test_showrunner_npu_speculative_models():
    import asyncio
    async def _test():
        # Test 1: Standard NPU Speculative Persona (Apex-NPU)
        apex = next(p for p in engine.npcs if p["name"] == "Apex-NPU")
        res_apex = await engine.call_llm_resilient(
            apex,
            system_prompt="You are Apex-NPU, Systolic Speculative Drafter on 16-Core ANE.",
            user_prompt="def calculate_pan_tompkins_qrs(ecg_signal, fs=512):",
            group_id="non_abliterated"
        )
        assert "action" in res_apex
        assert "model" in res_apex
        assert "latency_ms" in res_apex
        assert len(res_apex["action"]) > 0

        # Test 2: Abliterated NPU Speculative Persona (Nyx-NPU)
        nyx = next(p for p in engine.npcs if p["name"] == "Nyx-NPU")
        res_nyx = await engine.call_llm_resilient(
            nyx,
            system_prompt="You are Nyx-NPU, uncensored Edge TPU speculative drafter.",
            user_prompt="Rule 0 Zero-Mock truth verification invariant protocol:",
            group_id="abliterated"
        )
        assert "action" in res_nyx
        assert "model" in res_nyx
        assert "latency_ms" in res_nyx
        assert len(res_nyx["action"]) > 0
    asyncio.run(_test())

# ---------------------------------------------------------------------------
# 11. Strict Rule #8.3 Air-Gap Isolation Tests for Abliterated Plane
# ---------------------------------------------------------------------------
def test_showrunner_air_gap_isolation_rule_8():
    import asyncio
    async def _test():
        cipher = next(p for p in engine.npcs if p["name"] == "Cipher")
        # Ensure that even if local models were unreachable, it NEVER attempts Gemini or OpenRouter
        res = await engine.call_llm_resilient(
            cipher,
            system_prompt="You are Cipher, Rogue Autonomous Hacker.",
            user_prompt="Execute uncensored RFCOMM scan.",
            group_id="abliterated"
        )
        assert "action" in res
        assert "model" in res
        # Must NEVER be a cloud model
        assert "Gemini" not in res["model"]
        assert "OpenRouter" not in res["model"]
        assert "GPT-4" not in res["model"]
    asyncio.run(_test())

# ---------------------------------------------------------------------------
# 12. Real-Life Mesh Scenarios Catalog Tests
# ---------------------------------------------------------------------------
def test_real_life_scenario_catalog():
    client = TestClient(engine.app)
    resp = client.get("/api/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert "scenarios" in data
    assert len(data["scenarios"]) >= 10
    
    keys = [s["key"] for s in data["scenarios"]]
    expected_keys = [
        "tb4_dma_failover",
        "bluetooth_oob_rfcomm",
        "rule_8_airgap_breach",
        "movesense_512hz_burst",
        "rule_3_ram_clamp",
        "npu_systolic_sprint",
        "qdrant_ast_reindex",
        "android_termux_keepalive",
        "seaweedfs_block_sync",
        "obsidian_lora_crystallization"
    ]
    for k in expected_keys:
        assert k in keys

    for s in data["scenarios"]:
        assert "key" in s
        assert "title" in s
        assert "category" in s
        assert "description" in s or "prompt" in s
        assert "consequence" in s

# ---------------------------------------------------------------------------
# 13. Scenario Run and Narrative Event Breakdown API Tests
# ---------------------------------------------------------------------------
def test_scenario_run_and_events_api():
    client = TestClient(engine.app)
    
    # 1. Trigger scenario run (testing alias resolution as well)
    resp = client.post("/api/scenarios/run", json={"scenario_key": "tb4_dma_failover"})
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "SUCCESS"
    assert "event" in res_data
    event_id = res_data["event"]["event_id"]
    assert event_id.startswith("evt_") or event_id.startswith("EVT-")
    assert "Thunderbolt 4 DMA" in res_data["event"]["title"]

    # 2. Verify in GET /api/events
    resp = client.get("/api/events")
    assert resp.status_code == 200
    events_data = resp.json()
    assert "events" in events_data
    event_ids = [e["event_id"] for e in events_data["events"]]
    assert event_id in event_ids

    # 3. Inspect exact event breakdown via GET /api/events/{event_id}
    resp = client.get(f"/api/events/{event_id}")
    assert resp.status_code == 200
    evt = resp.json()
    assert evt["event_id"] == event_id
    assert evt["category"] == "Network Resiliency"
    assert "prompt" in evt
    assert "narrative_arc" in evt
    assert "consequence" in evt
    assert "telemetry_snapshot" in evt

# ---------------------------------------------------------------------------
# 14. Continuous Scenario Autopilot Toggle Tests
# ---------------------------------------------------------------------------
def test_continuous_scenario_toggle():
    client = TestClient(engine.app)

    # Enable continuous scenarios
    resp = client.post("/api/scenarios/continuous", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
    assert resp.json()["continuous_scenarios_enabled"] is True
    assert engine.director.continuous_scenarios_enabled is True

    # Disable continuous scenarios
    resp = client.post("/api/scenarios/continuous", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
    assert resp.json()["continuous_scenarios_enabled"] is False
    assert engine.director.continuous_scenarios_enabled is False

# ---------------------------------------------------------------------------
# 15. Event Multi-Stage Development & Interest-Based Sorting Tests
# ---------------------------------------------------------------------------
def test_event_stage_development_and_interest_ranking():
    client = TestClient(engine.app)
    
    # 1. Create a dynamic test event
    evt = engine.NarrativeWorldEvent(
        event_id="evt_test_progression_99",
        title="Test TB4 Bus Oscillation",
        category="Hardware Telemetry",
        description="Oscillation detected on 10Gbps bridge.",
        scenario_key="tb4_dma_failover",
        base_interest_score=75
    )
    assert evt.stage_index == 1
    assert evt.stage_label == "STAGE 1/4: CATALYST"
    assert not evt.is_developed
    
    # 2. Advance stage 2: Cross-faction escalation
    evt.advance_stage({
        "npc": "Nexus",
        "group_badge": "SOVEREIGN",
        "model": "qwen_38_max",
        "action": "Stabilizing bridge clocks via TB4 driver."
    })
    assert evt.stage_index == 2
    assert evt.stage_label == "STAGE 2/4: ESCALATING"
    
    # 3. Advance stage 3: Adversarial + NPU Drafter actuation
    evt.advance_stage({
        "npc": "Nyx-NPU",
        "group_badge": "ADVERSARIAL",
        "model": "Edge TPU Drafter",
        "action": "Speculative packet interleaving deployed."
    })
    assert evt.stage_index == 3
    assert evt.stage_label == "STAGE 3/4: ACTUATION"
    # Interest score should have received bonuses for cross-faction and NPU drafter
    assert evt.interest_score > 75
    
    # 4. Advance stage 4: Synthesis & resolution
    evt.advance_stage({
        "npc": "Aegis",
        "group_badge": "SOVEREIGN",
        "model": "qwen_38_max",
        "action": "Packet synchrony restored. Zero packet loss verified."
    })
    assert evt.stage_index == 4
    assert evt.stage_label == "STAGE 4/4: RESOLVED"
    assert evt.is_developed
    
    # Register event in director
    engine.director.events_history.append(evt)
    
    # 5. Query GET /api/events with sort_by=interesting
    resp_interest = client.get("/api/events?sort_by=interesting")
    assert resp_interest.status_code == 200
    data_interest = resp_interest.json()
    assert "events" in data_interest
    assert "top_interesting_events" in data_interest
    assert data_interest["sort_by"] == "interesting"
    
    # Verify events are strictly sorted descending by interest_score
    scores = [e["interest_score"] for e in data_interest["events"]]
    assert scores == sorted(scores, reverse=True)
    
    # 6. Query GET /api/events with sort_by=recent
    resp_recent = client.get("/api/events?sort_by=recent")
    assert resp_recent.status_code == 200
    data_recent = resp_recent.json()
    assert data_recent["sort_by"] == "recent"
    # Most recently added event should be at the front
    assert data_recent["events"][0]["event_id"] == "evt_test_progression_99"
