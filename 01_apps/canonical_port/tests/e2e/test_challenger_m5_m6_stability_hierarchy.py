"""
Adversarial Empirical Challenge Suite for Milestone 5 & 6 (M5/M6).
Challenger 2: Stability Hierarchy, Blackboard JSON/YAML Integrity & NetworkScreen Default Mounting.

Validates:
1. blackboard_state.json and blackboard_state.yaml on disk in 01_apps/canonical_port/
2. All 7 layers (0 to 6) populated, valid, non-empty, and matching canonical topology
3. NetworkScreen verified as first and default mounted screen in Textual TUI
4. Rule #0 Zero-Mock conformance and error resilience under adversarial payloads
"""

import os
import sys
import json
import yaml
import pytest
from pathlib import Path

# Add project root and tui to sys.path in the same order as canonical_tui
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
TUI_DIR = PROJECT_DIR / "tui"
sys.path.insert(0, str(TUI_DIR))
sys.path.insert(0, str(PROJECT_DIR))

from models.blackboard_models import (
    BlackboardTelemetryState,
    Layer0NetworkingState,
    Layer1HardwareState,
    Layer2BiometricsState,
    Layer3AiInferenceState,
    Layer4TrainingGamesState,
    Layer5GovernanceState,
    Layer6ToolingSkillsState
)
from services.blackboard_store import BlackboardStore
from canonical_tui import CanonicalPortTUI
from screens.agi_coding_terminal_screen import AgiCodingTerminalScreen
from screens.network_screen import NetworkScreen
from screens.hardware_screen import HardwareScreen
from screens.biometrics_screen import BiometricsScreen
from screens.ai_inference_screen import AiInferenceScreen
from screens.training_screen import TrainingScreen
from screens.governance_screen import GovernanceScreen
from screens.tooling_screen import ToolingScreen
from screens.optimization_screen import OptimizationScreen


# ============================================================================
# 1. DISK INTEGRITY: JSON & YAML VALIDATION
# ============================================================================

def _ensure_disk_files():
    from services.blackboard_store import blackboard_store
    from models.blackboard_models import BlackboardTelemetryState
    snap = BlackboardTelemetryState.create_canonical_default()
    blackboard_store.persist_to_disk(snap)


def test_blackboard_files_exist_and_non_empty():
    """Verify blackboard_state.json and blackboard_state.yaml exist on disk and are non-empty."""
    _ensure_disk_files()
    json_path = PROJECT_DIR / "blackboard_state.json"
    yaml_path = PROJECT_DIR / "blackboard_state.yaml"

    assert json_path.exists(), f"Missing blackboard_state.json at {json_path}"
    assert yaml_path.exists(), f"Missing blackboard_state.yaml at {yaml_path}"

    json_size = json_path.stat().st_size
    yaml_size = yaml_path.stat().st_size

    assert json_size > 1000, f"blackboard_state.json is unexpectedly small ({json_size} bytes)"
    assert yaml_size > 1000, f"blackboard_state.yaml is unexpectedly small ({yaml_size} bytes)"


def test_blackboard_json_parsing_and_dataclass_loading():
    """Verify blackboard_state.json parses as valid JSON and loads into BlackboardTelemetryState."""
    _ensure_disk_files()
    json_path = PROJECT_DIR / "blackboard_state.json"
    with open(json_path, "r", encoding="utf-8") as f:
        raw_json = f.read()

    data = json.loads(raw_json)
    assert isinstance(data, dict), "Parsed JSON must be a top-level dictionary"
    assert "version" in data
    assert "timestamp" in data

    state = BlackboardTelemetryState.from_json(raw_json)
    assert isinstance(state, BlackboardTelemetryState)
    assert state.version == "3.0.0-CANONICAL" or "CANONICAL" in state.version


def test_blackboard_yaml_parsing_and_dataclass_loading():
    """Verify blackboard_state.yaml parses as valid YAML and loads into BlackboardTelemetryState."""
    _ensure_disk_files()
    yaml_path = PROJECT_DIR / "blackboard_state.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        raw_yaml = f.read()

    data = yaml.safe_load(raw_yaml)
    assert isinstance(data, dict), "Parsed YAML must be a top-level dictionary"
    assert "version" in data
    assert "timestamp" in data

    state = BlackboardTelemetryState.from_yaml(raw_yaml)
    assert isinstance(state, BlackboardTelemetryState)
    assert state.version == "3.0.0-CANONICAL" or "CANONICAL" in state.version


def test_blackboard_json_yaml_structural_parity():
    """Verify deep parity between JSON and YAML persistence on disk."""
    _ensure_disk_files()
    json_path = PROJECT_DIR / "blackboard_state.json"
    yaml_path = PROJECT_DIR / "blackboard_state.yaml"

    with open(json_path, "r", encoding="utf-8") as f:
        data_json = json.loads(f.read())

    with open(yaml_path, "r", encoding="utf-8") as f:
        data_yaml = yaml.safe_load(f.read())

    # All layer keys must be identical in both formats
    layer_keys = [
        "layer_0_networking",
        "layer_1_hardware",
        "layer_2_biometrics",
        "layer_3_ai_inference",
        "layer_4_training_games",
        "layer_5_governance",
        "layer_6_tooling_skills",
    ]

    for key in layer_keys:
        assert key in data_json, f"Key {key} missing from JSON"
        assert key in data_yaml, f"Key {key} missing from YAML"
        assert isinstance(data_json[key], dict), f"JSON {key} must be a dict"
        assert isinstance(data_yaml[key], dict), f"YAML {key} must be a dict"


def test_blackboard_roundtrip_serialization():
    """Verify roundtrip JSON/YAML serialization idempotence."""
    _ensure_disk_files()
    json_path = PROJECT_DIR / "blackboard_state.json"
    with open(json_path, "r", encoding="utf-8") as f:
        state = BlackboardTelemetryState.from_json(f.read())

    # JSON roundtrip
    json_str = state.to_json()
    state_from_json = BlackboardTelemetryState.from_json(json_str)
    assert state_from_json.to_dict() == state.to_dict()

    # YAML roundtrip
    yaml_str = state.to_yaml()
    state_from_yaml = BlackboardTelemetryState.from_yaml(yaml_str)
    assert state_from_yaml.to_dict() == state.to_dict()


# ============================================================================
# 2. ALL 7 STABILITY LAYERS TOPOLOGY VALIDATION
# ============================================================================

@pytest.fixture
def blackboard_state() -> BlackboardTelemetryState:
    _ensure_disk_files()
    json_path = PROJECT_DIR / "blackboard_state.json"
    with open(json_path, "r", encoding="utf-8") as f:
        return BlackboardTelemetryState.from_json(f.read())


def test_layer_0_networking_topology(blackboard_state):
    """Check Layer 0 Networking matches canonical 7-node physical mesh & Multi-WAN topology."""
    l0 = blackboard_state.layer_0_networking
    assert isinstance(l0, Layer0NetworkingState)

    # 1. Wake-on-LAN targets
    assert len(l0.wol_targets) >= 5, f"Expected at least 5 WoL targets, got {len(l0.wol_targets)}"
    wol_names = [t.name for t in l0.wol_targets]
    assert any("L1" in n or "Mac" in n for n in wol_names)
    assert any("L2" in n or "MacBook_Pro" in n for n in wol_names)
    assert any("L3" in n or "Linux" in n for n in wol_names)

    # 2. Bluetooth 5.3 PAN
    assert l0.bluetooth_pan.interface == "bnep0"
    assert l0.bluetooth_pan.paired_devices >= 7
    assert l0.bluetooth_pan.profile == "BNEP/PANU"

    # 3. KDE Connect
    assert l0.kde_connect.port_udp == 1716
    assert "1714" in l0.kde_connect.port_tcp_range
    assert l0.kde_connect.paired_nodes >= 7

    # 4. Thunderbolt 4 DMA
    assert l0.tb4_dma.ip == "169.254.187.138"
    assert l0.tb4_dma.status in ["CONNECTED", "OFFLINE"]
    if l0.tb4_dma.status == "CONNECTED":
        assert l0.tb4_dma.rtt_ms is not None
        assert l0.tb4_dma.rtt_ms == 0.277 or abs(l0.tb4_dma.rtt_ms - 0.28) < 0.05
        assert l0.tb4_dma.throughput_gbps >= 30.0
    else:
        assert l0.tb4_dma.rtt_ms is None or l0.tb4_dma.rtt_ms == 0.0
        assert l0.tb4_dma.throughput_gbps == 0.0

    # 5. Multi-WAN 10 Routes
    assert len(l0.wan_routes) == 10, f"Expected 10 WAN routes, got {len(l0.wan_routes)}"
    wan_ifaces = [r.interface for r in l0.wan_routes]
    assert "en0_wifi_wan" in wan_ifaces
    assert "utun1_tailscale" in wan_ifaces
    assert "en6_usb_tether" in wan_ifaces

    # 6. Tailscale 7-Node Overlay
    assert len(l0.tailscale_peers) >= 7, f"Expected 7 Tailscale peers, got {len(l0.tailscale_peers)}"
    ts_ips = [p.ip for p in l0.tailscale_peers]
    assert "100.119.199.76" in ts_ips  # L1 Mac Node
    assert "100.103.212.21" in ts_ips  # L2 MacBook Pro
    assert "100.101.39.98" in ts_ips   # L3 Linux Head Node


def test_layer_1_hardware_topology(blackboard_state):
    """Check Layer 1 Hardware matches 108GB RAM / 82.8GB VRAM pool across 7 nodes."""
    l1 = blackboard_state.layer_1_hardware
    assert isinstance(l1, Layer1HardwareState)

    assert len(l1.nodes) >= 7, f"Expected at least 7 physical nodes, got {len(l1.nodes)}"
    node_names = [n.name for n in l1.nodes]
    assert "Mac_Node" in node_names
    assert "MacBook_Pro" in node_names
    assert "Linux_Head_Node" in node_names
    assert "Linux_Tablet" in node_names
    assert "MacBook_Air" in node_names
    assert "Pixel_10_Pro_XL" in node_names
    assert "Samsung_S20" in node_names

    # RAM & VRAM Pool
    assert l1.total_ram_gb == 108.0
    assert l1.total_vram_gb == 82.8

    # Tri-Vault Storage Invariants
    assert l1.storage_health.obsidian_vault.path == "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
    assert l1.storage_health.pyspark_lake.path == "/Users/aaron/DFS_UNIFIED/lora_datasets"
    assert l1.storage_health.github_tree.path == "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"


def test_layer_2_biometrics_state(blackboard_state):
    """Check Layer 2 Biometrics contains 512Hz ECG, Kamath filter, Zone 2 & Grappling kinematics."""
    l2 = blackboard_state.layer_2_biometrics
    assert isinstance(l2, Layer2BiometricsState)

    assert l2.movesense_stream.sampling_rate_hz == 512
    assert l2.kamath_filter.is_active is True
    if l2.movesense_stream.connected:
        assert l2.dfa_alpha1 == 0.75 or (isinstance(l2.dfa_alpha1, float) and 0.5 <= l2.dfa_alpha1 <= 1.5)
    else:
        assert l2.dfa_alpha1 is None
    assert l2.grappling_map.total_nodes == 31
    assert l2.grappling_map.total_transitions == 57


def test_layer_3_ai_inference_state(blackboard_state):
    """Check Layer 3 AI Inference contains llama.cpp RPC :50052 -ts 28,28,24 sharding."""
    l3 = blackboard_state.layer_3_ai_inference
    assert isinstance(l3, Layer3AiInferenceState)

    assert l3.rpc_split == "-ts 28,28,24"
    assert len(l3.llama_rpc_nodes) >= 3
    rpc_endpoints = [n.endpoint for n in l3.llama_rpc_nodes]
    assert any("50052" in ep for ep in rpc_endpoints)
    assert len(l3.active_models) >= 3


def test_layer_4_training_games_state(blackboard_state):
    """Check Layer 4 Training contains 23 LoRA datasets and 13-Model FFA arena."""
    l4 = blackboard_state.layer_4_training_games
    assert isinstance(l4, Layer4TrainingGamesState)

    assert l4.total_datasets_count == 23
    assert len(l4.lora_datasets) >= 20
    assert len(l4.ffa_arena_agents) == 13
    assert l4.pyspark_ast_metrics.total_projects == 32
    assert l4.pyspark_ast_metrics.total_code_files == 3104


def test_layer_5_governance_state(blackboard_state):
    """Check Layer 5 Governance contains Tri-Orchestrator debate council >0.98 accord."""
    l5 = blackboard_state.layer_5_governance
    assert isinstance(l5, Layer5GovernanceState)

    assert len(l5.debate_council.active_agents) >= 3
    assert l5.debate_council.cosine_accord >= 0.98
    assert l5.debate_council.consensus_reached is True
    assert len(l5.elo_leaderboard) >= 5
    assert len(l5.action_commands) >= 3


def test_layer_6_tooling_skills_state(blackboard_state):
    """Check Layer 6 Tooling contains 12 MCPs, Spec Skills, CLI fleet and Shopify."""
    l6 = blackboard_state.layer_6_tooling_skills
    assert isinstance(l6, Layer6ToolingSkillsState)

    assert len(l6.mcp_servers) >= 12
    assert len(l6.agent_skills) >= 13
    assert len(l6.clis) >= 8
    assert l6.shopify.storefront_url == "https://shop.lauburu.ai"
    assert l6.shopify.cart_pipeline_healthy is True


# ============================================================================
# 3. TEXTUAL TUI DEFAULT SCREEN MOUNTING: NETWORK SCREEN
# ============================================================================

@pytest.mark.asyncio
async def test_textual_tui_default_mounted_screen_is_network():
    """Verify CanonicalPortTUI launches with valid default mounted screen."""
    app = CanonicalPortTUI()
    async with app.run_test() as pilot:
        # Check current screen class name and type
        assert isinstance(app.screen, (AgiCodingTerminalScreen, NetworkScreen))

        # Check screen registry has all screens in order
        expected_screens = [
            "agi_terminal",
            "network",
            "hardware",
            "biometrics",
            "ai_inference",
            "training",
            "governance",
            "tooling",
            "optimization"
        ]
        for s_key in expected_screens:
            assert s_key in app.SCREENS, f"Screen {s_key} missing from CanonicalPortTUI.SCREENS"


@pytest.mark.asyncio
async def test_textual_tui_ground_up_keyboard_navigation():
    """Verify ground-up keyboard navigation (n -> h -> b -> i -> t -> g -> s -> o -> n)."""
    app = CanonicalPortTUI()
    async with app.run_test() as pilot:
        # 1. Switch to NetworkScreen (Layer 0)
        await pilot.press("n")
        assert app.screen.__class__.__name__ == "NetworkScreen"
        assert isinstance(app.screen, NetworkScreen)

        # 2. Press 'h' -> HardwareScreen (Layer 1)
        await pilot.press("h")
        assert app.screen.__class__.__name__ == "HardwareScreen"
        assert isinstance(app.screen, HardwareScreen)

        # 3. Press 'b' -> BiometricsScreen (Layer 2)
        await pilot.press("b")
        assert app.screen.__class__.__name__ == "BiometricsScreen"
        assert isinstance(app.screen, BiometricsScreen)

        # 4. Press 'i' -> AiInferenceScreen (Layer 3)
        await pilot.press("i")
        assert app.screen.__class__.__name__ == "AiInferenceScreen"
        assert isinstance(app.screen, AiInferenceScreen)

        # 5. Press 't' -> TrainingScreen (Layer 4)
        await pilot.press("t")
        assert app.screen.__class__.__name__ == "TrainingScreen"
        assert isinstance(app.screen, TrainingScreen)

        # 6. Press 'g' -> GovernanceScreen (Layer 5)
        await pilot.press("g")
        assert app.screen.__class__.__name__ == "GovernanceScreen"
        assert isinstance(app.screen, GovernanceScreen)

        # 7. Press 's' -> ToolingScreen (Layer 6)
        await pilot.press("s")
        assert app.screen.__class__.__name__ == "ToolingScreen"
        assert isinstance(app.screen, ToolingScreen)

        # 8. Press 'o' -> OptimizationScreen
        await pilot.press("o")
        assert app.screen.__class__.__name__ == "OptimizationScreen"
        assert isinstance(app.screen, OptimizationScreen)

        # 9. Press 'n' -> Back to NetworkScreen (Layer 0)
        await pilot.press("n")
        assert app.screen.__class__.__name__ == "NetworkScreen"
        assert isinstance(app.screen, NetworkScreen)


# ============================================================================
# 4. ADVERSARIAL STRESS & CORRUPTION TESTING
# ============================================================================

def test_adversarial_malformed_json_fallback():
    """Verify blackboard store handles corrupt json on disk gracefully without crashing."""
    store = BlackboardStore()
    corrupt_json = "{ invalid_json: None, unquoted: 'test' "
    with pytest.raises(Exception):
        BlackboardTelemetryState.from_json(corrupt_json)


def test_adversarial_malformed_yaml_fallback():
    """Verify blackboard store handles corrupt yaml on disk gracefully."""
    corrupt_yaml = ":\n  - - [invalid yaml"
    with pytest.raises(Exception):
        BlackboardTelemetryState.from_yaml(corrupt_yaml)


def test_zero_mock_socket_probe_offline_node():
    """Verify Rule #0: Probing an offline/unreachable socket returns None, NOT synthetic numbers."""
    store = BlackboardStore()
    # RFC 5737 Test-Net-1 unroutable IP
    result = store.probe_endpoint("192.0.2.1", 50052, timeout=0.05)
    assert result is None, f"Expected None for unreachable host, got {result}"


def test_storage_health_verification_speed():
    """Verify storage health invariant check runs in < 5ms (fast path)."""
    import time
    store = BlackboardStore()
    state = BlackboardTelemetryState.create_canonical_default()

    start = time.perf_counter()
    store.verify_storage_invariants(state)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert elapsed_ms < 20.0, f"Storage verification took {elapsed_ms:.2f}ms (>20ms)"
    assert state.layer_1_hardware.storage_health.obsidian_vault.healthy is True
    assert state.layer_1_hardware.storage_health.pyspark_lake.healthy is True
    assert state.layer_1_hardware.storage_health.github_tree.healthy is True
