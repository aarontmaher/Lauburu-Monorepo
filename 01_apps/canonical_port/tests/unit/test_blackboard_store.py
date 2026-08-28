"""
Unit Tests: Canonical Telemetry Blackboard Data Models & Store Service (M2)
Validates strongly typed Python dataclasses across all 7 ground-up stability layers,
round-trip JSON/YAML serialization, thread-safe mutation, atomic disk persistence,
Rule #0 zero-mock compliance, and socket probe resilience.
"""

import os
import sys
import json
import time
import socket
import tempfile
import threading
import pytest
import yaml
from typing import Dict, Any

# Ensure tui package is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))
from models.blackboard_models import (
    BlackboardTelemetryState,
    BlackboardProvenance,
    Layer0NetworkingState,
    Layer1HardwareState,
    Layer2BiometricsState,
    Layer3AiInferenceState,
    Layer4TrainingGamesState,
    Layer5GovernanceState,
    Layer6ToolingSkillsState,
    WolTarget,
    BluetoothPanLink,
    KdeConnectState,
    Tb4DmaInterconnect,
    WanRoute,
    TailscalePeer,
    HardwareNodeState,
    ObsidianVaultState,
    PySparkLakeState,
    GitHubTreeState,
    TriVaultStorageState,
    MovesenseStreamState,
    KamathFilterState,
    PttBloodPressure,
    ImuKinematicsState,
    GrapplingMapState,
    LlamaRpcNode,
    InferenceModelInfo,
    PetalsSwarmState,
    ExoP2PState,
    LoraDatasetInfo,
    LossDecayPoint,
    FfaArenaAgent,
    PySparkAstMetrics,
    TriOrchestratorDebateState,
    EloLeaderboardEntry,
    SwarmActionCommand,
    McpServerInfo,
    SdkInfo,
    CliToolInfo,
    AgentSkillInfo,
    ShopifyCommerceState,
    VoiceCodingState,
    VoiceTelemetry,
    VoiceStatus,
    VOICE_STATUS_IDLE,
    VOICE_STATUS_LISTENING,
    VOICE_STATUS_THINKING,
    VOICE_STATUS_SPEAKING,
    VOICE_STATUS_MUTED,
    VOICE_STATUS_ERROR
)
from services.blackboard_store import BlackboardStore, blackboard_store


# ============================================================================
# 1. LAYER 0 NETWORKING MODEL TESTS
# ============================================================================

def test_layer_0_networking_instantiation_and_defaults():
    """Verify Layer 0 models: WoL, BT PAN, KDE Connect, TB4 DMA, Multi-WAN, Tailscale."""
    state = Layer0NetworkingState()
    assert isinstance(state.wol_targets, list)
    assert isinstance(state.bluetooth_pan, BluetoothPanLink)
    assert state.bluetooth_pan.interface == "bnep0"
    assert state.bluetooth_pan.rtt_ms == 0.03
    assert state.bluetooth_pan.bandwidth == "3.0 MB/s"
    assert state.bluetooth_pan.paired_devices == 7

    assert isinstance(state.kde_connect, KdeConnectState)
    assert state.kde_connect.port_udp == 1716
    assert state.kde_connect.port_tcp_range == "1714-1764"
    assert state.kde_connect.paired_nodes == 7
    assert state.kde_connect.tls_encrypted is True

    assert isinstance(state.tb4_dma, Tb4DmaInterconnect)
    assert state.tb4_dma.ip == "169.254.187.138"
    assert state.tb4_dma.rtt_ms == 0.277
    assert state.tb4_dma.throughput_gbps == 38.4
    assert state.tb4_dma.zero_copy_active is True

    assert state.ewma_alpha == 0.35
    assert state.circuit_breaker_trip_threshold == 0.284


def test_layer_0_canonical_defaults():
    """Verify canonical Layer 0 populates all 5 WoL targets, 10 WAN routes, and 7 Tailscale peers."""
    root = BlackboardTelemetryState.create_canonical_default()
    l0 = root.layer_0_networking

    assert len(l0.wol_targets) == 5
    wol_names = {t.name for t in l0.wol_targets}
    assert "L1_Mac_Mini_Host" in wol_names
    assert "L2_MacBook_Pro_Vault" in wol_names
    assert "L3_Linux_Head_Node" in wol_names
    assert "L4_Linux_Tablet" in wol_names
    assert "L5_MacBook_Air" in wol_names

    assert len(l0.wan_routes) == 10
    routes_by_iface = {r.interface: r for r in l0.wan_routes}
    assert "en0_wifi_wan" in routes_by_iface
    assert "utun1_tailscale" in routes_by_iface
    assert "en6_usb_tether" in routes_by_iface
    assert "cloudflare_quic" in routes_by_iface
    assert "p01_tb4_dma" in routes_by_iface
    assert "p02_10gbe" in routes_by_iface
    assert "p03_usb32_adb" in routes_by_iface

    assert len(l0.tailscale_peers) == 7
    peers_by_ip = {p.node_name: p.ip for p in l0.tailscale_peers}
    assert peers_by_ip["Mac_Node"] == "100.119.199.76"
    assert peers_by_ip["MacBook_Pro"] == "100.103.212.21"
    assert peers_by_ip["Linux_Head_Node"] == "100.101.39.98"
    assert peers_by_ip["Linux_Tablet"] == "100.81.92.125"
    assert peers_by_ip["MacBook_Air"] == "100.93.158.96"
    assert peers_by_ip["Pixel_10_Pro_XL"] == "100.73.38.87"
    assert peers_by_ip["Samsung_S20"] == "100.84.40.95"


# ============================================================================
# 2. LAYER 1 HARDWARE & STORAGE MODEL TESTS
# ============================================================================

def test_layer_1_hardware_and_trivault_storage():
    """Verify Layer 1 hardware nodes, memory ceilings, and Tri-Vault storage invariants."""
    root = BlackboardTelemetryState.create_canonical_default()
    l1 = root.layer_1_hardware

    assert len(l1.nodes) == 8  # 7 nodes + 1 GW
    assert l1.total_ram_gb == 108.0
    assert l1.total_vram_gb == 82.8
    assert l1.pooled_ram_used_gb == 48.2
    assert l1.pooled_vram_used_gb == 39.0
    assert l1.memory_governor_active is True

    # Tri-Vault storage
    storage = l1.storage_health
    assert isinstance(storage.obsidian_vault, ObsidianVaultState)
    assert isinstance(storage.pyspark_lake, PySparkLakeState)
    assert isinstance(storage.github_tree, GitHubTreeState)
    assert storage.obsidian_vault.path == "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
    assert storage.pyspark_lake.path == "/Users/aaron/DFS_UNIFIED/lora_datasets"
    assert storage.github_tree.path == "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
    assert storage.pyspark_lake.headroom_threshold_gb == 10.0
    assert storage.all_healthy is True

    # Node attributes
    node_map = {n.node_id: n for n in l1.nodes}
    assert node_map["L1"].name == "Mac_Node"
    assert node_map["L1"].ram_total_gb == 24.0
    assert node_map["L1"].vram_cap_gb == 21.6
    assert node_map["L1"].dynamic_cap_pct == 90.0

    assert node_map["L2"].name == "MacBook_Pro"
    assert node_map["L2"].ram_total_gb == 16.0
    assert node_map["L2"].vram_cap_gb == 14.0
    assert node_map["L2"].storage_free_gb == 409.3

    assert node_map["L3"].name == "Linux_Head_Node"
    assert node_map["L3"].dynamic_cap_pct == 80.0

    assert node_map["L6"].name == "Pixel_10_Pro_XL"
    assert node_map["L6"].qi_power_watts == 15.0


# ============================================================================
# 3. LAYER 2 BIOMETRICS & KINEMATICS MODEL TESTS
# ============================================================================

def test_layer_2_biometrics_and_grappling_map():
    """Verify Layer 2 Movesense 512Hz ECG, Kamath 20% filter, Zone 2 threshold, 31 OPML nodes."""
    root = BlackboardTelemetryState.create_canonical_default()
    l2 = root.layer_2_biometrics

    assert l2.movesense_stream.connected is True
    assert l2.movesense_stream.sampling_rate_hz == 512
    assert l2.movesense_stream.profile == "zone2"
    assert l2.movesense_stream.medical_class == "Class IIa"
    assert l2.movesense_stream.ecg_snr_db == 28.5

    assert l2.kamath_filter.filter_name == "Kamath 20% Clinical RR Filter"
    assert l2.kamath_filter.threshold_pct == 20.0
    assert l2.kamath_filter.is_active is True

    assert l2.heart_rate_bpm == 138.4
    assert len(l2.rr_intervals_ms) == 5
    assert l2.rmssd_ms == 42.8
    assert l2.dfa_alpha1 == 0.75
    assert l2.zone2_status == "ZONE_2_OPTIMAL"
    assert l2.vo2_max_ml_kg_min == 52.4

    assert l2.ptt_blood_pressure.systolic_mmhg == 118
    assert l2.ptt_blood_pressure.diastolic_mmhg == 76
    assert l2.ptt_blood_pressure.pulse_transit_time_ms == 212.4

    assert l2.imu_kinematics.cadence_spm == 164
    assert l2.imu_kinematics.mechanical_power_watts == 182.4
    assert l2.imu_kinematics.total_dynamic_g == 0.99

    assert l2.grappling_map.total_nodes == 31
    assert l2.grappling_map.total_transitions == 57
    assert l2.grappling_map.world_bounds_m == {"x": 8.0, "y": 8.0, "z": 2.5}
    assert len(l2.grappling_map.tactical_categories) == 8
    assert len(l2.grappling_map.recent_submissions) == 5


# ============================================================================
# 4. LAYER 3 AI INFERENCE & SHARDING MODEL TESTS
# ============================================================================

def test_layer_3_ai_inference_and_model_mesh():
    """Verify Layer 3 llama.cpp RPC :50052 (-ts 28,28,24), 7 active models, Petals, Exo."""
    root = BlackboardTelemetryState.create_canonical_default()
    l3 = root.layer_3_ai_inference

    assert l3.rpc_split == "-ts 28,28,24"
    assert l3.total_sharded_layers == 80
    assert len(l3.llama_rpc_nodes) == 6
    assert len([n for n in l3.llama_rpc_nodes if n.status == "ONLINE"]) == 3
    total_sharded = sum(n.layers_sharded for n in l3.llama_rpc_nodes)
    total_vram = sum(n.vram_used_gb for n in l3.llama_rpc_nodes)
    assert total_sharded == 80
    assert total_vram == 39.0

    assert len(l3.active_models) >= 7
    model_ids = {m.model_id for m in l3.active_models}
    assert "kimi_tandem_titan" in model_ids
    assert "kimi_vl_thinking_2506" in model_ids
    assert "qwen_38_max" in model_ids
    assert "genetic_moe_core" in model_ids
    assert "gemini_flash_cloud" in model_ids
    assert "deepseek_v3_671b" in model_ids
    assert "llama_33_70b" in model_ids

    assert l3.petals_swarm.port == 31337
    assert l3.petals_swarm.active_blocks == 80
    assert l3.exo_p2p.port == 52415
    assert l3.exo_p2p.topology == "Ring-P2P"


# ============================================================================
# 5. LAYER 4 TRAINING & GAMES ARENA MODEL TESTS
# ============================================================================

def test_layer_4_training_and_ffa_arena():
    """Verify Layer 4: 23 LoRA datasets, loss decay 1.84 -> 0.142, 13 FFA agents, PySpark AST."""
    root = BlackboardTelemetryState.create_canonical_default()
    l4 = root.layer_4_training_games

    assert l4.total_datasets_count == 23
    assert len(l4.lora_datasets) == 23
    dataset_names = [d.name for d in l4.lora_datasets]
    assert "continuous_lora_dataset.jsonl" in dataset_names
    assert "biometrics_sleep_lora_dataset.jsonl" in dataset_names
    assert "truth_audit_debate.jsonl" in dataset_names
    assert "ui_ux_improvements.jsonl" in dataset_names

    assert l4.initial_loss == 2.18
    assert l4.current_loss == 0.142
    assert l4.training_step == 4800
    assert len(l4.loss_history) == 7
    assert l4.loss_history[0].loss == 1.84
    assert l4.loss_history[-1].loss == 0.142

    assert l4.total_harvested_pairs == 84320
    assert l4.harvest_rate_pairs_per_min == 48.5

    assert len(l4.ffa_arena_agents) == 13
    assert l4.ffa_arena_agents[0].model_id == "kimi_titan"
    assert l4.ffa_arena_agents[0].hp == 95

    # PySpark AST Metrics
    ast = l4.pyspark_ast_metrics
    assert ast.total_projects == 32
    assert ast.total_code_files == 3104
    assert ast.total_loc == 434965
    assert ast.total_test_suites == 325
    assert ast.total_ast_nodes == 124491
    assert ast.language_breakdown["Python"] == 752
    assert ast.language_breakdown["Markdown"] == 2228


# ============================================================================
# 6. LAYER 5 GOVERNANCE & DEBATE MODEL TESTS
# ============================================================================

def test_layer_5_governance_and_action_commands():
    """Verify Layer 5 Tri-Orchestrator debate (>0.98 accord), ELO leaderboard, 6 action commands."""
    root = BlackboardTelemetryState.create_canonical_default()
    l5 = root.layer_5_governance

    assert l5.debate_council.cosine_accord == 0.986
    assert l5.debate_council.threshold == 0.98
    assert l5.debate_council.consensus_reached is True
    assert l5.debate_council.current_turn == 3
    assert l5.debate_council.total_turns == 4
    assert l5.debate_council.current_phase == "ACCORD_SYNTHESIS"
    assert len(l5.debate_council.active_agents) == 4

    assert len(l5.elo_leaderboard) == 7
    assert l5.elo_leaderboard[0].rank == 1
    assert l5.elo_leaderboard[0].name == "Gemini 3.7 Flash Cloud"
    assert l5.elo_leaderboard[0].rating == 2240
    assert l5.elo_leaderboard[1].name == "Kimi 72B/88B Tandem Titan"
    assert l5.elo_leaderboard[1].rating == 2180

    assert len(l5.action_commands) == 6
    cmds = {c.command for c in l5.action_commands}
    assert "/audit" in cmds
    assert "/duel" in cmds
    assert "/cron" in cmds
    assert "/storage" in cmds
    assert "/ping" in cmds
    assert "/revive" in cmds


# ============================================================================
# 7. LAYER 6 TOOLING, SKILLS & COMMERCE MODEL TESTS
# ============================================================================

def test_layer_6_tooling_skills_and_shopify():
    """Verify Layer 6: 12 MCP servers, 12 SDKs, 10 CLIs, Spec-00 to Spec-12, Shopify."""
    root = BlackboardTelemetryState.create_canonical_default()
    l6 = root.layer_6_tooling_skills

    assert len(l6.mcp_servers) == 12
    mcp_names = {s.name for s in l6.mcp_servers}
    assert "docker" in mcp_names
    assert "obsidian" in mcp_names
    assert "cloudflare" in mcp_names
    assert "computer-use" in mcp_names
    assert "browser-use" in mcp_names
    assert "antigravity-models" in mcp_names
    assert "figma" in mcp_names
    assert "marionette-mcp" in mcp_names
    assert "filesystem" in mcp_names
    assert "memory" in mcp_names
    assert "sequential-thinking" in mcp_names
    assert "chrome-devtools-mcp" in mcp_names

    assert len(l6.sdks) == 12
    sdk_names = {s.name for s in l6.sdks}
    assert "torch" in sdk_names
    assert "pyspark" in sdk_names
    assert "transformers" in sdk_names
    assert "peft" in sdk_names
    assert "trl" in sdk_names
    assert "accelerate" in sdk_names
    assert "llama_cpp" in sdk_names
    assert "google_antigravity_sdk" in sdk_names
    assert "textual" in sdk_names
    assert "psutil" in sdk_names
    assert "pydantic" in sdk_names
    assert "asyncssh" in sdk_names

    assert len(l6.clis) == 10
    cli_names = {c.name for c in l6.clis}
    assert "agy" in cli_names
    assert "gh" in cli_names
    assert "uv" in cli_names
    assert "adb" in cli_names
    assert "ssh" in cli_names
    assert "docker" in cli_names
    assert "kdeconnect-cli" in cli_names
    assert "tailscale" in cli_names
    assert "weed" in cli_names
    assert "scrcpy" in cli_names

    assert len(l6.agent_skills) == 13
    assert l6.agent_skills[0].name == "spec-00-core-infrastructure"
    assert l6.agent_skills[-1].name == "spec-12-continuous-lora-evolution"

    assert l6.shopify.storefront_url == "https://shop.lauburu.ai"
    assert l6.shopify.subscription_tier == "Titanium All-Access"
    assert l6.shopify.active_memberships == 1420
    assert l6.shopify.merchandise_catalog_synced is True


# ============================================================================
# 8. ROOT STATE SERIALIZATION & ROUNDTRIP TESTS (DICT, JSON, YAML)
# ============================================================================

def test_blackboard_state_to_dict_and_from_dict_roundtrip():
    """Verify dictionary serialization and lossless reconstruction."""
    original = BlackboardTelemetryState.create_canonical_default()
    d = original.to_dict()

    assert isinstance(d, dict)
    assert d["version"] == "3.0.0-CANONICAL"
    assert d["source_node"] == "L1_Mac_Node"
    assert d["provenance"]["rule_zero_certified"] is True

    reconstructed = BlackboardTelemetryState.from_dict(d)
    assert reconstructed.version == original.version
    assert reconstructed.source_node == original.source_node
    assert len(reconstructed.layer_0_networking.wol_targets) == 5
    assert len(reconstructed.layer_1_hardware.nodes) == 8
    assert reconstructed.layer_2_biometrics.heart_rate_bpm == 138.4
    assert reconstructed.layer_3_ai_inference.total_sharded_layers == 80
    assert len(reconstructed.layer_4_training_games.lora_datasets) == 23
    assert reconstructed.layer_5_governance.debate_council.cosine_accord == 0.986
    assert len(reconstructed.layer_6_tooling_skills.mcp_servers) == 12


def test_blackboard_state_to_json_and_from_json_roundtrip():
    """Verify JSON string serialization and lossless reconstruction for AGI ingestion."""
    original = BlackboardTelemetryState.create_canonical_default()
    json_str = original.to_json(indent=2)

    assert isinstance(json_str, str)
    assert '"version": "3.0.0-CANONICAL"' in json_str
    assert '"169.254.187.138"' in json_str

    reconstructed = BlackboardTelemetryState.from_json(json_str)
    assert reconstructed.version == original.version
    assert reconstructed.layer_0_networking.tb4_dma.throughput_gbps == 38.4
    assert reconstructed.layer_1_hardware.storage_health.all_healthy is True
    assert reconstructed.layer_2_biometrics.grappling_map.total_nodes == 31
    assert reconstructed.layer_4_training_games.current_loss == 0.142


def test_blackboard_state_to_yaml_and_from_yaml_roundtrip():
    """Verify YAML string serialization and lossless reconstruction for compact LLM context."""
    original = BlackboardTelemetryState.create_canonical_default()
    yaml_str = original.to_yaml()

    assert isinstance(yaml_str, str)
    assert "version: 3.0.0-CANONICAL" in yaml_str
    assert "source_node: L1_Mac_Node" in yaml_str

    reconstructed = BlackboardTelemetryState.from_yaml(yaml_str)
    assert reconstructed.version == original.version
    assert reconstructed.layer_2_biometrics.movesense_stream.sampling_rate_hz == 512
    assert reconstructed.layer_5_governance.debate_council.current_phase == "ACCORD_SYNTHESIS"
    assert len(reconstructed.layer_6_tooling_skills.clis) == 10


# ============================================================================
# 9. BLACKBOARD STORE SERVICE & ATOMIC PERSISTENCE TESTS
# ============================================================================

def test_blackboard_store_initialization_and_snapshot():
    """Verify BlackboardStore singleton initialization and snapshot retrieval."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, cache_ttl_seconds=0.5, auto_persist=True)
        snapshot = store.get_snapshot()

        assert isinstance(snapshot, BlackboardTelemetryState)
        assert snapshot.version == "3.0.0-CANONICAL"
        assert os.path.isfile(os.path.join(tmpdir, "blackboard_state.json"))
        assert os.path.isfile(os.path.join(tmpdir, "blackboard_state.yaml"))


def test_blackboard_store_atomic_persistence_and_load():
    """Verify atomic disk persistence and subsequent loading from disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)
        snapshot = store.get_snapshot()

        # Modify state
        snapshot.layer_2_biometrics.heart_rate_bpm = 152.0
        success = store.persist_to_disk(snapshot)
        assert success is True

        # Load back in fresh store instance
        store2 = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)
        loaded = store2.load_from_disk()

        assert loaded is not None
        assert loaded.layer_2_biometrics.heart_rate_bpm == 152.0
        assert loaded.version == "3.0.0-CANONICAL"


def test_blackboard_store_update_layer():
    """Verify update_layer for dictionary and dataclass payloads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=True)

        # 1. Update with dict
        bio_dict = store.get_snapshot().layer_2_biometrics.to_dict()
        bio_dict["heart_rate_bpm"] = 160.5
        bio_dict["zone2_status"] = "THRESHOLD_REACHED"

        updated = store.update_layer("layer_2_biometrics", bio_dict)
        assert updated.layer_2_biometrics.heart_rate_bpm == 160.5
        assert updated.layer_2_biometrics.zone2_status == "THRESHOLD_REACHED"

        # 2. Update with dataclass instance
        new_gov = Layer5GovernanceState(
            debate_council=TriOrchestratorDebateState(cosine_accord=0.999, consensus_reached=True)
        )
        updated2 = store.update_layer("governance", new_gov)
        assert updated2.layer_5_governance.debate_council.cosine_accord == 0.999

        # 3. Invalid layer key raises ValueError
        with pytest.raises(ValueError):
            store.update_layer("invalid_layer_xyz", {})


def test_blackboard_store_headless_agi_apis():
    """Verify Master AGI headless methods: get_raw_state_for_agi, to_json, to_yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)

        raw = store.get_raw_state_for_agi()
        assert isinstance(raw, dict)
        assert "version" in raw
        assert "layer_0_networking" in raw
        assert "layer_1_hardware" in raw
        assert "layer_2_biometrics" in raw
        assert "layer_3_ai_inference" in raw
        assert "layer_4_training_games" in raw
        assert "layer_5_governance" in raw
        assert "layer_6_tooling_skills" in raw

        json_out = store.to_json(indent=2)
        assert isinstance(json_out, str)
        assert '"version": "3.0.0-CANONICAL"' in json_out

        yaml_out = store.to_yaml()
        assert isinstance(yaml_out, str)
        assert "version: 3.0.0-CANONICAL" in yaml_out


# ============================================================================
# 10. THREAD-SAFETY & SOCKET PROBING (RULE #0 ZERO-MOCK VERIFICATION)
# ============================================================================

def test_blackboard_store_thread_safe_concurrent_access():
    """Verify high-concurrency multi-threaded access without race conditions or deadlocks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, cache_ttl_seconds=0.01, auto_persist=True)
        errors = []

        def worker_read(worker_id: int):
            try:
                for _ in range(25):
                    snap = store.get_snapshot(force_refresh=True)
                    assert snap.version == "3.0.0-CANONICAL"
                    raw = store.get_raw_state_for_agi()
                    assert len(raw["layer_1_hardware"]["nodes"]) == 8
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def worker_write(worker_id: int):
            try:
                for i in range(15):
                    bio = store.get_snapshot().layer_2_biometrics.to_dict()
                    bio["heart_rate_bpm"] = 120.0 + (worker_id * 5) + i
                    store.update_layer("layer_2", bio)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(6):
            threads.append(threading.Thread(target=worker_read, args=(i,)))
        for i in range(4):
            threads.append(threading.Thread(target=worker_write, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors encountered: {errors}"


def test_socket_probe_live_and_offline_resilience():
    """
    Verify live socket probing returns actual latency on open ports and
    authentic None on offline/closed ports (Rule #0 Zero-Mock compliant).
    """
    store = BlackboardStore()

    # 1. Probe closed/unreachable port -> must return None (not fake jitter)
    res_closed = store.probe_endpoint("127.0.0.1", 59997, timeout=0.05)
    assert res_closed is None

    # 2. Start a temporary real TCP server to verify genuine RTT measurement
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    port = server_sock.getsockname()[1]
    server_sock.listen(1)

    try:
        res_open = store.probe_endpoint("127.0.0.1", port, timeout=0.20)
        assert res_open is not None
        assert isinstance(res_open, float)
        assert res_open >= 0.0
    finally:
        server_sock.close()


def test_dynamic_mac_mini_ip_resolution():
    """
    Verify Mac Mini IP resolution dynamically queries active interfaces
    and returns a valid IPv4 string without hardcoding stale addresses.
    """
    store = BlackboardStore()
    ip = store.resolve_mac_mini_ip()
    assert isinstance(ip, str)
    assert len(ip.split(".")) == 4
    # All octets must be integers between 0 and 255
    octets = [int(o) for o in ip.split(".")]
    assert len(octets) == 4
    for o in octets:
        assert 0 <= o <= 255

    snapshot = store.get_snapshot(force_refresh=True)
    l1_node = next(n for n in snapshot.layer_1_hardware.nodes if n.node_id == "L1")
    assert l1_node.ip == ip
    l1_wol = next(w for w in snapshot.layer_0_networking.wol_targets if w.name == "L1_Mac_Mini_Host")
    assert l1_wol.ip == ip


def test_tb4_dma_ping_probe_offline_and_connected():
    """
    Verify TB4 DMA probe returns OFFLINE with None latency when unreachable (100% loss)
    and CONNECTED with positive RTT when reachable.
    """
    store = BlackboardStore()
    tb4 = store.probe_tb4_dma("169.254.187.138", timeout_ms=100)
    assert isinstance(tb4.status, str)
    if tb4.status == "OFFLINE":
        assert tb4.rtt_ms is None or tb4.rtt_ms == 0.0
        assert tb4.throughput_gbps == 0.0
        assert tb4.zero_copy_active is False
    else:
        assert tb4.rtt_ms > 0.0
        assert tb4.throughput_gbps > 0.0
        assert tb4.zero_copy_active is True


def test_tailscale_live_probe_peer_parsing():
    """
    Verify Tailscale peer probe parses live CLI status or falls back cleanly.
    """
    store = BlackboardStore()
    peers = store.probe_tailscale_peers()
    assert isinstance(peers, list)
    for p in peers:
        assert hasattr(p, "node_name")
        assert hasattr(p, "ip")
        assert hasattr(p, "status")
        assert p.status in ["ONLINE", "OFFLINE", "IDLE"]


def test_biometrics_authentic_fallback_on_zero_sensors():
    """
    Verify biometrics returns authentic waiting states (None / AWAITING_BLUETOOTH_SENSORS)
    when Port 4000 reports 0 connected sensors or is unreachable.
    """
    store = BlackboardStore()
    snapshot = store.get_snapshot(force_refresh=True)
    bio = snapshot.layer_2_biometrics

    # If Port 4000 is not running or movesense is disconnected
    if not bio.movesense_stream.connected:
        assert bio.heart_rate_bpm is None
        assert bio.rmssd_ms is None
        assert bio.dfa_alpha1 is None
        assert bio.zone2_status == "AWAITING_BLUETOOTH_SENSORS"
        assert bio.ptt_blood_pressure.systolic_mmhg is None
        assert bio.ptt_blood_pressure.diastolic_mmhg is None
        assert bio.ptt_blood_pressure.status == "OFFLINE"


def test_petals_and_exo_socket_probes_offline_fallback():
    """
    Verify Petals DHT and Exo P2P sockets report OFFLINE with 0 blocks/peers
    when ports 31337 and 52415 are closed.
    """
    store = BlackboardStore()
    snapshot = store.get_snapshot(force_refresh=True)
    ai = snapshot.layer_3_ai_inference

    # If Petals is offline
    if ai.petals_swarm.status == "OFFLINE":
        assert ai.petals_swarm.dht_connected is False
        assert ai.petals_swarm.active_blocks == 0
        assert ai.petals_swarm.swarm_nodes == 0

    # If Exo is offline
    if ai.exo_p2p.status == "OFFLINE":
        assert ai.exo_p2p.discovery_ring is False
        assert ai.exo_p2p.active_peers == 0
        assert ai.exo_p2p.topology == "DISCONNECTED"
        assert ai.exo_p2p.ring_latency_ms is None


def test_macbook_air_l5_priority_elevation_over_l2():
    """
    Verify MacBook Air (L5, Apple M4, 14GB AI VRAM cap, 90% dynamic) is #2 priority node,
    ranked strictly above MacBook Pro (L2) in hardware priority ranking and nodes ordering.
    """
    store = BlackboardStore()
    snapshot = store.get_snapshot(force_refresh=True)
    nodes = snapshot.layer_1_hardware.nodes
    node_map = {n.node_id: n for n in nodes}

    assert "L5" in node_map
    assert "L2" in node_map
    l5 = node_map["L5"]
    l2 = node_map["L2"]

    assert l5.priority_rank == 2
    assert l2.priority_rank == 3
    assert l5.priority_rank < l2.priority_rank

    # In nodes list, L5 must appear before L2
    l5_idx = next(i for i, n in enumerate(nodes) if n.node_id == "L5")
    l2_idx = next(i for i, n in enumerate(nodes) if n.node_id == "L2")
    assert l5_idx < l2_idx
    assert l5_idx == 1  # 2nd in list after L1


def test_macbook_pro_l2_model_string_correction():
    """
    Verify L2 MacBook Pro display string is updated to 'Apple Silicon TB4 Bridge Node'.
    """
    store = BlackboardStore()
    snapshot = store.get_snapshot(force_refresh=True)
    l2 = next(n for n in snapshot.layer_1_hardware.nodes if n.node_id == "L2")
    assert l2.model == "Apple Silicon TB4 Bridge Node"


def test_headless_device_capability_scores_across_all_nodes():
    """
    Verify headless capability tracking and exact scores across all 8 nodes:
    GW: 100, L1: 95, L3: 92, L6: 88, L7: 80, L4: 75, L5: 72, L2: 70.
    """
    expected_scores = {
        "GW": 100,
        "L1": 95,
        "L3": 92,
        "L6": 88,
        "L7": 80,
        "L4": 75,
        "L5": 72,
        "L2": 70
    }
    store = BlackboardStore()
    snapshot = store.get_snapshot(force_refresh=True)
    node_map = {n.node_id: n for n in snapshot.layer_1_hardware.nodes}

    for node_id, exp_score in expected_scores.items():
        assert node_id in node_map, f"Node {node_id} missing from hardware state"
        node = node_map[node_id]
        assert node.headless_capable is True
        assert node.headless_score == exp_score, f"Node {node_id} expected score {exp_score}, got {node.headless_score}"


def test_device_elo_ratings_across_all_nodes():
    """
    Verify device ELO rating is tracked for every hardware node.
    """
    store = BlackboardStore()
    snapshot = store.get_snapshot(force_refresh=True)
    for node in snapshot.layer_1_hardware.nodes:
        assert hasattr(node, "device_elo_rating")
        assert isinstance(node.device_elo_rating, float)
        assert 1000.0 <= node.device_elo_rating <= 2000.0


def test_tri_orchestrator_infinite_consensus_protocol_no_turn_caps():
    """
    Verify debate turn caps are abolished, using Infinite Consensus Protocol
    with Code-Off deadlock resolution and human fallback.
    """
    store = BlackboardStore()
    snapshot = store.get_snapshot(force_refresh=True)
    debate = snapshot.layer_5_governance.tri_orchestrator_debate

    assert debate.protocol_type == "Infinite Consensus Protocol"
    assert debate.max_turns is None
    assert hasattr(debate, "code_off_active")
    assert hasattr(debate, "human_fallback_active")


# ============================================================================
# 11. MILESTONE M2: BACKGROUND POLLER & INSTANT RETRIEVAL (<1ms) TESTS (F11)
# ============================================================================

def test_blackboard_store_autonomous_background_poller_lifecycle():
    """
    Verify start_background_poller starts a daemon thread, continuously refreshes
    the cached snapshot in the background, and stop_background_poller cleans up.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)
        assert not store.is_poller_running

        # Start background poller with fast interval
        store.start_background_poller(interval=0.1)
        assert store.is_poller_running

        # Let background poller run a few cycles
        time.sleep(0.35)

        # Snapshot should be populated and recent
        snap = store.get_snapshot(force_refresh=False)
        assert snap is not None
        assert snap.version == "3.0.0-CANONICAL"

        # Stop background poller
        store.stop_background_poller(timeout=1.0)
        assert not store.is_poller_running


def test_blackboard_store_instant_snapshot_retrieval_under_1ms():
    """
    Verify get_snapshot(force_refresh=False) executes in sub-millisecond time (<1ms)
    when cached state exists.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)
        # Prime cache
        store.get_snapshot(force_refresh=True)

        latencies_ms = []
        for _ in range(50):
            t0 = time.perf_counter()
            snap = store.get_snapshot(force_refresh=False)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(dt_ms)
            assert snap.version == "3.0.0-CANONICAL"

        avg_latency = sum(latencies_ms) / len(latencies_ms)
        max_latency = max(latencies_ms)
        # Average retrieval must be well below 1.0ms (typically <0.05ms)
        assert avg_latency < 1.0, f"Average snapshot retrieval latency too high: {avg_latency:.4f}ms"
        assert max_latency < 5.0, f"Max snapshot retrieval latency too high: {max_latency:.4f}ms"


def test_blackboard_store_background_poller_idempotency():
    """
    Verify calling start_background_poller multiple times does not spawn duplicate threads.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)
        store.start_background_poller(interval=0.1)
        thread1 = store._poller_thread

        # Second start call with different interval
        store.start_background_poller(interval=0.15)
        thread2 = store._poller_thread

        assert thread1 is thread2
        assert store.is_poller_running

        store.stop_background_poller()
        assert not store.is_poller_running


def test_blackboard_store_bounded_memory_over_extended_polling_cycles():
    """
    Verify that repeated polling and snapshot retrieval cycles are strictly bounded in memory
    and do not leak objects or unbounded history queues over hundreds of iterations.
    """
    import gc
    import tracemalloc

    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)
        gc.collect()
        tracemalloc.start()

        snapshot_start = tracemalloc.take_snapshot()

        # Execute 500 snapshot cycles
        for _ in range(500):
            _ = store.get_snapshot(force_refresh=False)

        gc.collect()
        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot_end.compare_to(snapshot_start, 'lineno')
        total_diff_kb = sum(stat.size_diff for stat in top_stats) / 1024.0

        # Memory diff should be tightly bounded (under 250 KB for 500 in-memory cycles)
        assert total_diff_kb < 250.0, f"Memory growth exceeded bound: {total_diff_kb:.2f} KB"


# ============================================================================
# 12. VOICE CODING & S2S STREAMING BLACKBOARD INTEGRATION TESTS
# ============================================================================

def test_blackboard_store_voice_coding_state_integration():
    """
    Verify voice_coding state models, default status IDLE, update_voice_state,
    update_voice_telemetry, and layer updates via update_layer('voice_coding', ...).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)
        vc = store.get_voice_state()
        assert isinstance(vc, VoiceCodingState)
        assert vc.status == "IDLE"
        assert vc.endpoint_ws == "ws://127.0.0.1:8765/ws/voice"

        # Update voice state to LISTENING
        snap1 = store.update_voice_state("LISTENING", current_transcript="def calculate_total():")
        assert snap1.voice_coding.status == "LISTENING"
        assert snap1.voice_coding.is_stt_active is True
        assert snap1.voice_coding.current_transcript == "def calculate_total():"

        # Update telemetry
        snap2 = store.update_voice_telemetry(input_db=-21.5, latency_ms=11.2, vad_active=True)
        assert snap2.voice_coding.telemetry.input_db == -21.5
        assert snap2.voice_coding.telemetry.latency_ms == 11.2
        assert snap2.voice_coding.telemetry.vad_active is True

        # Test dictionary roundtrip
        d = snap2.to_dict()
        assert "voice_coding" in d
        assert d["voice_coding"]["status"] == "LISTENING"
        assert d["voice_coding"]["telemetry"]["input_db"] == -21.5

        reconstructed = BlackboardTelemetryState.from_dict(d)
        assert reconstructed.voice_coding.status == "LISTENING"
        assert reconstructed.voice_coding.current_transcript == "def calculate_total():"



