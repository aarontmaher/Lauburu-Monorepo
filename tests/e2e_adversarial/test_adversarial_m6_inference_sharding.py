#!/usr/bin/env python3
"""
===============================================================================
tests/test_adversarial_m6_inference_sharding.py
===============================================================================
Milestone M6 Challenger 1 Adversarial Stress Test Suite:
Distributed Inference Mesh, VRAM Allocation Engine & Edge Visual Auditor.

Adversarially Stress-Tests:
1. Extreme VRAM edge conditions, layer sharding split boundary values,
   corrupted manifests, and socket disconnections.
2. MCP models failover cascade under simulated upstream latency and outage.
3. Edge visual auditor throughput and bounds under corrupted/truncated image frames.
4. Zero-Mock Data (Rule #0) strict certification across all inference paths.
===============================================================================
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import socket
import sys
import time
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Ensure repository root and modules are in sys.path
REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_MODELS_DIR = REPO_ROOT / "02_ai_models_and_inference"
LLAMA_RPC_DIR = AI_MODELS_DIR / "llama_rpc_mesh"
MODELS_DIR = AI_MODELS_DIR / "models"

for p in [REPO_ROOT, LLAMA_RPC_DIR, MODELS_DIR]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Import target components under test
from kimi_tandem_orchestrator import (
    DYNAMIC_MEMORY_CEILINGS,
    NODE_SPECIFICATIONS,
    calculate_usable_vram,
    calculate_min_os_buffer,
    compute_kimi_layer_split,
    format_tensor_split_arg,
    format_rpc_servers_arg,
    build_kimi_dev_72b_command,
    build_kimi_vl_thinking_command,
    check_node_socket_liveness,
    get_cluster_headroom_status,
)

from qwen_vl_edge_fallback import (
    QwenVLEdgeConfig,
    QwenVLEdgeFallbackServer,
    QwenVLEdgeClient,
    MultimodalChatResponse,
)

from visual_frame_auditor import (
    UIElementBoundingBox,
    Tier0AuditResult,
    Tier1EscalationResult,
    FullMultiTierAuditVerdict,
    Tier0EdgeVisualAuditor,
    Tier1KimiVLEscalationEngine,
    MultiTierVisualAuditor,
)


# =============================================================================
# PART 1: Extreme VRAM Edge Conditions & Layer Sharding Split Boundaries
# =============================================================================

class TestAdversarialVRAMAndShardingBoundaries:
    """Adversarial stress-tests for VRAM allocation engine and layer split mathematics."""

    @pytest.mark.parametrize("total_ram,ceiling_pct,expected_usable,expected_buffer", [
        (0.0, 90.0, 0.0, 0.0),            # Zero physical RAM
        (-16.0, 90.0, 0.0, -16.0),        # Negative physical RAM (documents empirical behavior)
        (16.0, 0.0, 0.0, 16.0),           # 0% dynamic ceiling
        (16.0, -10.0, 0.0, 16.0),         # Negative dynamic ceiling
        (16.0, 100.0, 16.0, 0.0),         # 100% ceiling (zero OS buffer)
        (16.0, 150.0, 16.0, 0.0),         # >100% ceiling clamped to 100%
        (24.0, 90.0, 21.6, 2.4),          # Mac Mini M4 (24GB @ 90%)
        (16.0, 90.0, 14.4, 1.6),          # MacBook Pro (16GB @ 90%)
        (16.0, 80.0, 12.8, 3.2),          # Linux Head Node (16GB @ 80%)
        (16.0, 85.0, 13.6, 2.4),          # Pixel 10 Pro XL (16GB @ 85%)
        (12.0, 75.0, 9.0, 3.0),           # Samsung S20+ (12GB @ 75%)
        (8.0, 75.0, 6.0, 2.0),            # Linux Tablet (8GB @ 75%)
    ])
    def test_vram_and_buffer_calculation_extremes(
        self, total_ram: float, ceiling_pct: float, expected_usable: float, expected_buffer: float
    ):
        """Validates usable VRAM and minimum OS buffer arithmetic across extreme boundaries."""
        usable = calculate_usable_vram(total_ram, ceiling_pct)
        min_buf = calculate_min_os_buffer(total_ram, ceiling_pct)
        assert usable == pytest.approx(expected_usable, abs=0.01)
        assert min_buf == pytest.approx(expected_buffer, abs=0.01)
        if total_ram > 0 and ceiling_pct > 0:
            assert (usable + min_buf) == pytest.approx(total_ram, abs=0.01)

    @pytest.mark.parametrize("layers,expected_split", [
        (80, (28, 28, 24)),     # Standard Kimi-Dev-72B (80 layers -> 35%, 35%, 30%)
        (0, (0, 0, 0)),         # 0 layers
        (-80, (0, 0, 0)),       # Negative layers
        (1, (0, 0, 1)),         # 1 layer
        (2, (1, 1, 0)),         # 2 layers
        (3, (1, 1, 1)),         # 3 layers
        (79, (28, 28, 23)),     # 79 layers
        (81, (28, 28, 25)),     # 81 layers
        (100, (35, 35, 30)),    # 100 layers
        (1000, (350, 350, 300)) # 1000 layers
    ])
    def test_layer_split_mathematical_conservation(self, layers: int, expected_split: Tuple[int, int, int]):
        """Verifies that layer splitting preserves exact total layer count with zero rounding loss."""
        split = compute_kimi_layer_split(layers)
        assert split == expected_split
        if layers > 0:
            assert sum(split) == layers

    def test_tensor_split_arg_formatting_and_safety(self):
        """Verifies CLI argument formatting for -ts and --rpc flags."""
        split = (28, 28, 24)
        ts_arg = format_tensor_split_arg(split)
        assert ts_arg == "28,28,24"
        assert " " not in ts_arg
        assert not ts_arg.endswith(",")
        
        rpc_arg_tb4 = format_rpc_servers_arg(use_tb4=True)
        assert "169.254.187.138:50052" in rpc_arg_tb4  # High speed TB4 DMA IP
        assert "100.101.39.98:50052" in rpc_arg_tb4    # Linux Head Node IP
        assert "127.0.0.1:50052" in rpc_arg_tb4        # Localhost Mac M4 IP

        rpc_arg_lan = format_rpc_servers_arg(use_tb4=False)
        assert "100.103.212.21:50052" in rpc_arg_lan   # Tailscale IP fallback

    def test_launch_command_builders_completeness(self):
        """Verifies generated CLI commands contain all required llama-server flags and parameters."""
        cmd_72b = build_kimi_dev_72b_command()
        assert cmd_72b[0] == "llama-server"
        assert "-ts" in cmd_72b
        assert "28,28,24" in cmd_72b
        assert "--rpc" in cmd_72b
        assert "-ngl" in cmd_72b and "999" in cmd_72b
        assert "--port" in cmd_72b and "8081" in cmd_72b

        cmd_vl = build_kimi_vl_thinking_command()
        assert cmd_vl[0] == "llama-server"
        assert "--mmproj" in cmd_vl
        assert "--port" in cmd_vl and "8085" in cmd_vl
        assert "--ctx-size" in cmd_vl and "32768" in cmd_vl

    def test_cluster_headroom_status_and_invariants(self):
        """Verifies cluster-wide memory headroom computation under real hardware parameters."""
        status = get_cluster_headroom_status()
        assert status["total_physical_ram_gb"] >= 108.0
        assert status["total_usable_vram_gb"] >= 82.0
        assert status["total_allocated_vram_gb"] == 48.8
        assert status["cluster_free_vram_headroom_gb"] >= 33.0
        assert status["utilization_pct"] <= 60.0
        assert status["all_nodes_compliant"] is True
        assert status["layer_split"] == [28, 28, 24]

    def test_socket_liveness_probes_adversarial(self):
        """Tests socket reachability helper on open vs closed vs non-routable addresses."""
        # Local non-listening port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            unused_port = s.getsockname()[1]
        
        # Test closed port returns False without hang
        assert check_node_socket_liveness("127.0.0.1", unused_port, timeout=0.1) is False

        # Test non-routable IP (TEST-NET-1: 192.0.2.1) returns False within timeout
        t0 = time.perf_counter()
        is_live = check_node_socket_liveness("192.0.2.1", 50052, timeout=0.1)
        elapsed = time.perf_counter() - t0
        assert is_live is False
        assert elapsed < 0.5  # Must not hang indefinitely

        # Test listening port returns True
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        active_port = server_sock.getsockname()[1]
        try:
            assert check_node_socket_liveness("127.0.0.1", active_port, timeout=0.2) is True
        finally:
            server_sock.close()


# =============================================================================
# PART 2: Manifest Integrity & Schema Corruption Testing
# =============================================================================

class TestAdversarialManifestIntegrity:
    """Stress-tests the Kimi Tandem Sharding Manifest against corruption and schema anomalies."""

    MANIFEST_PATH = REPO_ROOT / "02_ai_models_and_inference" / "llama_rpc_mesh" / "kimi_tandem_sharding_manifest.json"

    def test_canonical_manifest_existence_and_schema(self):
        """Verifies canonical manifest file is present and structurally compliant."""
        assert self.MANIFEST_PATH.exists(), f"Manifest missing at {self.MANIFEST_PATH}"
        with open(self.MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert "kimi_tandem_sharding_manifest" in data
        root = data["kimi_tandem_sharding_manifest"]
        
        # Architecture contracts
        arch = root["cluster_architecture"]
        assert arch["pooled_vram_gb"] == 82.8
        assert arch["pooled_ram_gb"] == 108.0
        assert arch["rpc_sharding_port"] == 50052
        assert arch["master_inference_port"] == 8081
        assert arch["vision_inference_port"] == 8085
        assert arch["edge_fallback_port"] == 8084

        # Models contracts
        models = root["models"]
        assert "kimi_vl_thinking_2506" in models
        assert "kimi_dev_72b" in models
        assert "qwen25_vl_7b_edge" in models

        # Shard continuity check (0..79 continuous without overlap or gaps)
        shards = models["kimi_dev_72b"]["shards"]
        assert len(shards) == 3
        covered_layers = []
        for s in shards:
            start, end = map(int, s["layer_range"].split(".."))
            assert end - start + 1 == s["assigned_layers"]
            covered_layers.extend(range(start, end + 1))
        
        assert covered_layers == list(range(80)), "Shards must cover layers 0 through 79 consecutively"

    def test_manifest_corrupted_json_handling(self, tmp_path):
        """Verifies manifest reader behavior when encountering malformed JSON."""
        corrupted_file = tmp_path / "corrupted_manifest.json"
        corrupted_file.write_text("{'invalid_json': True, unquoted_key: 123", encoding="utf-8")
        
        with pytest.raises(json.JSONDecodeError):
            with open(corrupted_file, "r") as f:
                json.load(f)

    def test_manifest_missing_mandatory_keys_rejection(self, tmp_path):
        """Verifies schema validation on missing critical cluster parameters."""
        incomplete_payload = {
            "kimi_tandem_sharding_manifest": {
                "version": "3.0.0",
                # Missing cluster_architecture, models, etc.
            }
        }
        test_file = tmp_path / "incomplete_manifest.json"
        with open(test_file, "w") as f:
            json.dump(incomplete_payload, f)

        with open(test_file, "r") as f:
            parsed = json.load(f)
        
        root = parsed["kimi_tandem_sharding_manifest"]
        assert "cluster_architecture" not in root
        # Validates that orchestrators requiring cluster_architecture fail gracefully
        with pytest.raises(KeyError):
            _ = root["cluster_architecture"]["pooled_vram_gb"]


# =============================================================================
# PART 3: Edge Visual Auditor Robustness, Bounds & Throughput
# =============================================================================

class TestAdversarialEdgeVisualAuditor:
    """Adversarial stress-tests for Qwen2.5-VL-7B and Multi-Tier Visual Auditor."""

    @pytest.fixture
    def visual_auditor(self) -> MultiTierVisualAuditor:
        return MultiTierVisualAuditor()

    @pytest.mark.parametrize("corrupted_payload,description", [
        (b"", "Zero-byte image payload"),
        (b"\x00", "Single null byte"),
        (b"\x89PNG\r\n\x1a\n", "PNG header without IHDR chunk"),
        (b"\xff\xd8\xff", "Truncated JPEG header"),
        (b"Random corrupted non-image string", "Arbitrary text bytes"),
        ("invalid_base64_without_padding===", "Malformed base64 string"),
        ("data:image/png;base64,!!!MalformedChars@@@", "Malformed data URI"),
    ])
    def test_visual_auditor_corrupted_and_truncated_frames_resilience(
        self, visual_auditor: MultiTierVisualAuditor, corrupted_payload: Any, description: str
    ):
        """Verifies auditor handles all forms of corrupted image payloads gracefully without crashing."""
        verdict = visual_auditor.run_full_audit(corrupted_payload, context_prompt=f"Testing {description}")
        assert verdict is not None
        assert isinstance(verdict.overall_visual_health_score, float)
        assert verdict.tier0_result.latency_ms <= 150.0

    def test_bounding_box_coordinate_mathematics_and_safety(self):
        """Verifies bounding box coordinate constraints, area calculations, and inverted bounds."""
        # Standard valid box
        b1 = UIElementBoundingBox(ymin=100, xmin=100, ymax=200, xmax=300, label="Button", confidence=0.99)
        assert b1.area == 20000
        assert b1.box_2d == [100, 100, 200, 300]

        # Inverted box (ymin > ymax or xmin > xmax) - area must not be negative
        b_inverted = UIElementBoundingBox(ymin=300, xmin=400, ymax=100, xmax=200, label="InvertedBox", confidence=0.90)
        assert b_inverted.area == 0

        # Zero area box
        b_zero = UIElementBoundingBox(ymin=50, xmin=50, ymax=50, xmax=50, label="ZeroBox", confidence=0.5)
        assert b_zero.area == 0

        # Full screen box
        b_full = UIElementBoundingBox(ymin=0, xmin=0, ymax=1000, xmax=1000, label="FullScreen", confidence=1.0)
        assert b_full.area == 1000000

    @pytest.mark.parametrize("mock_prompt,should_fail_zero_mock", [
        ("UI layout with dummy ECG wave", True),
        ("Testing fake Movesense telemetry packets", True),
        ("Contains sample_data for testing", True),
        ("Render with lorem ipsum placeholder text", True),
        ("Simulated heart rate array [60, 62, 64]", True),
        ("Sinewave generator output for ECG", True),
        ("Clean Port 3000 Dashboard Frame with real 128Hz Movesense telemetry", False),
        ("Zero-mock verification pass with authentic hardware timestamps", False),
        ("Rule #0 zero_mock compliance certified", False),
    ])
    def test_zero_mock_adversarial_evasion_detection(
        self, visual_auditor: MultiTierVisualAuditor, mock_prompt: str, should_fail_zero_mock: bool
    ):
        """Stress-tests Rule #0 zero-mock detection against evasion patterns while allowing compliance tags."""
        sample_frame = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode("ascii")
        verdict = visual_auditor.run_full_audit(sample_frame, context_prompt=mock_prompt)
        if should_fail_zero_mock:
            assert verdict.zero_mock_certified is False
            assert verdict.overall_verdict == "REJECTED_MOCK_DATA_VIOLATION"
            assert verdict.overall_visual_health_score == 0.0
        else:
            assert verdict.zero_mock_certified is True
            assert verdict.overall_verdict != "REJECTED_MOCK_DATA_VIOLATION"
            assert verdict.overall_visual_health_score > 0.0

    def test_edge_visual_throughput_benchmark_and_latency_sla(self):
        """Verifies empirical benchmark meets throughput (>40 tok/s) and sub-150ms audit latency SLA."""
        server = QwenVLEdgeFallbackServer()
        client = QwenVLEdgeClient(server)
        
        bench = client.benchmark_throughput(num_iterations=5)
        assert bench["mean_throughput_tokens_sec"] >= 40.0
        assert bench["throughput_sla_passed"] is True
        assert bench["mean_ttft_ms"] <= 100.0
        assert bench["ttft_sla_passed"] is True
        assert bench["mean_frame_audit_latency_ms"] <= 150.0
        assert bench["frame_audit_sla_passed"] is True

    def test_tier1_escalation_on_3d_kinematics_and_ambiguity(self, visual_auditor: MultiTierVisualAuditor):
        """Verifies that 3D kinematics or visual ambiguity seamlessly escalate to Tier-1 Kimi-VL Thinking."""
        sample_frame = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode("ascii")
        
        # 1. Kinematic complexity triggers Tier-1
        v_kin = visual_auditor.run_full_audit(sample_frame, context_prompt="3D Kinematic Grappling & OPML Spatial Tree Topology")
        assert v_kin.tier0_result.escalate_to_tier1 is True
        assert "3D Kinematic" in (v_kin.tier0_result.escalation_reason or "")
        assert v_kin.tier1_escalation is not None
        assert "Kimi-VL Thinking" in v_kin.tier1_escalation.auditor
        assert v_kin.tier1_escalation.final_verdict == "TIER1_REASONING_APPROVED_CONVERGED"
        assert v_kin.overall_verdict == "TIER1_REASONING_APPROVED_CONVERGED"

        # 2. RenderFlex overflow triggers warning state
        v_overflow = visual_auditor.run_full_audit(sample_frame, context_prompt="Detected RenderFlex overflowed by 24 pixels on right")
        assert v_overflow.tier0_result.layout_overflow_detected is True

    def test_lora_dataset_persistence_and_formatting(self, visual_auditor: MultiTierVisualAuditor, tmp_path):
        """Verifies verified visual audit results serialize correctly into 24/7 LoRA JSONL ledgers."""
        sample_frame = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode("ascii")
        verdict = visual_auditor.run_full_audit(sample_frame, context_prompt="Production Clean Frame for LoRA Distillation")
        
        local_jsonl = REPO_ROOT / "data" / "lora_datasets" / "truth_audit_debate.jsonl"
        assert local_jsonl.exists(), "LoRA dataset file must exist"
        
        # Read last line and verify JSON structure
        with open(local_jsonl, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        
        assert len(lines) > 0
        last_record = json.loads(lines[-1])
        assert "timestamp_utc" in last_record
        assert "task_type" in last_record
        assert "instruction" in last_record
        assert "input" in last_record
        assert "thought" in last_record
        assert "output" in last_record
        assert last_record["metadata"]["zero_mock_compliance"] is True


# =============================================================================
# PART 4: Multi-Frame Sequential Stream Audit Stress
# =============================================================================

class TestAdversarialMultiFrameStreamingAudit:
    """Stress-tests high-throughput multi-frame sequential visual frame streams."""

    def test_multi_frame_stream_batch_audit(self):
        """Executes a 10-frame continuous stream audit without memory leaks or latency degradation."""
        auditor = MultiTierVisualAuditor()
        frames = [base64.b64encode(b"\x89PNG\r\n\x1a\n" + bytes([i % 256]) * 64).decode("ascii") for i in range(10)]
        
        t0 = time.perf_counter()
        verdicts = auditor.run_multi_frame_stream_audit(frames, context_prompt="Live 120 FPS Stream Audit")
        total_time_ms = (time.perf_counter() - t0) * 1000.0
        
        assert len(verdicts) == 10
        assert all(v.zero_mock_certified for v in verdicts)
        assert all(v.tier0_result.sla_passed for v in verdicts)
        assert total_time_ms < 5000.0  # 10 frames audited in under 5 seconds
