"""
Deep Stress & Property Verification Suite for Milestone 2 (M2)
Tests Performance Invariants (<3ms fast path), Extreme Boundaries, and Zero-Mock Fidelity
"""

import os
import sys
import json
import yaml
import time
import socket
import tempfile
import threading
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))
from models.blackboard_models import (
    BlackboardTelemetryState,
    Layer0NetworkingState,
    Layer1HardwareState,
    Layer2BiometricsState,
    Layer3AiInferenceState,
    Layer4TrainingGamesState,
    Layer5GovernanceState,
    Layer6ToolingSkillsState,
    HardwareNodeState
)
from services.blackboard_store import BlackboardStore


def test_deep_storage_invariant_performance_fast_path():
    """Verify that verify_storage_invariants executes in < 3ms as specified in Section 6.3."""
    store = BlackboardStore()
    state = BlackboardTelemetryState.create_canonical_default()

    latencies_ms = []
    for _ in range(100):
        start = time.perf_counter()
        store.verify_storage_invariants(state)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        latencies_ms.append(elapsed_ms)

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    p95_latency = sorted(latencies_ms)[95]

    print(f"\nStorage Invariant Check Latency: Avg={avg_latency:.3f}ms, P95={p95_latency:.3f}ms")
    assert avg_latency < 3.0, f"Average storage check exceeded 3ms: {avg_latency:.3f}ms"
    assert p95_latency < 5.0, f"P95 storage check exceeded 5ms: {p95_latency:.3f}ms"


def test_deep_boundary_values_and_unicode_handling():
    """Verify models handle extreme numeric values and Unicode characters without truncation."""
    state = BlackboardTelemetryState.create_canonical_default()

    # Extreme numbers
    state.layer_1_hardware.total_ram_gb = 1000000.0
    state.layer_2_biometrics.heart_rate_bpm = 0.0
    state.layer_4_training_games.training_step = 2147483647
    state.layer_4_training_games.current_loss = 0.000000001

    # Special characters and unicode
    state.layer_0_networking.wol_targets[0].name = "Node-🚀-测试-Mini"
    state.layer_5_governance.debate_council.debate_topic = "Topic with symbols: <>&\"'/\n\t\r 🥋 ⚡"

    # Serialize to JSON and YAML
    json_str = state.to_json()
    yaml_str = state.to_yaml()

    # Reconstruct and verify
    from_j = BlackboardTelemetryState.from_json(json_str)
    assert from_j.layer_0_networking.wol_targets[0].name == "Node-🚀-测试-Mini"
    assert from_j.layer_5_governance.debate_council.debate_topic == "Topic with symbols: <>&\"'/\n\t\r 🥋 ⚡"
    assert from_j.layer_4_training_games.current_loss == 0.000000001
    assert from_j.layer_4_training_games.training_step == 2147483647

    from_y = BlackboardTelemetryState.from_yaml(yaml_str)
    assert from_y.layer_0_networking.wol_targets[0].name == "Node-🚀-测试-Mini"
    assert from_y.layer_1_hardware.total_ram_gb == 1000000.0


def test_deep_partial_dict_deserialization_defaults():
    """Verify that from_dict gracefully fills defaults when sub-dictionaries are missing or empty."""
    minimal_dict = {
        "version": "3.0.0-CUSTOM",
        "source_node": "L2_MacBook_Pro",
        "layer_0_networking": {},
        "layer_1_hardware": {},
        "layer_2_biometrics": {},
        "layer_3_ai_inference": {},
        "layer_4_training_games": {},
        "layer_5_governance": {},
        "layer_6_tooling_skills": {}
    }

    state = BlackboardTelemetryState.from_dict(minimal_dict)
    assert state.version == "3.0.0-CUSTOM"
    assert state.source_node == "L2_MacBook_Pro"
    assert isinstance(state.layer_0_networking, Layer0NetworkingState)
    assert isinstance(state.layer_1_hardware, Layer1HardwareState)
    assert isinstance(state.layer_2_biometrics, Layer2BiometricsState)
    assert isinstance(state.layer_3_ai_inference, Layer3AiInferenceState)
    assert isinstance(state.layer_4_training_games, Layer4TrainingGamesState)
    assert isinstance(state.layer_5_governance, Layer5GovernanceState)
    assert isinstance(state.layer_6_tooling_skills, Layer6ToolingSkillsState)


def test_deep_atomic_persistence_file_integrity():
    """Verify that persisted JSON and YAML files are valid, formatted, and strictly non-empty."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=True)
        snap = store.get_snapshot(force_refresh=True)

        json_file = os.path.join(tmpdir, "blackboard_state.json")
        yaml_file = os.path.join(tmpdir, "blackboard_state.yaml")

        assert os.path.exists(json_file)
        assert os.path.exists(yaml_file)
        assert os.path.getsize(json_file) > 1000  # Detailed payload is ~15-25KB
        assert os.path.getsize(yaml_file) > 1000

        with open(json_file, "r") as f:
            data_json = json.load(f)
            assert data_json["version"] == "3.0.0-CANONICAL"
            assert len(data_json["layer_0_networking"]["wol_targets"]) == 5
            assert len(data_json["layer_1_hardware"]["nodes"]) == 8
            assert len(data_json["layer_4_training_games"]["lora_datasets"]) == 23

        with open(yaml_file, "r") as f:
            data_yaml = yaml.safe_load(f)
            assert data_yaml["version"] == "3.0.0-CANONICAL"
            assert data_yaml["layer_2_biometrics"]["movesense_stream"]["sampling_rate_hz"] == 512
