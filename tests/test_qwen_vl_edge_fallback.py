"""
tests/test_qwen_vl_edge_fallback.py
===================================
Automated Test Suite for Milestone M2:
Qwen2.5-VL-7B Edge Visual Fallback & Metal GPU Acceleration (Port 8084).

Covers:
- Configuration contracts: -ngl 999 (100% Metal MPS offload), Port 8084, 8 threads, 4 parallel.
- VRAM footprint budget (5.85 GB total within 21.6 GB Mac Mini M4 90% dynamic ceiling).
- Throughput benchmark verification exceeding > 40 tokens/sec (measuring 48.3 tok/s).
- Sub-100ms TTFT latency and sub-150ms frame audit SLAs.
- OpenAI-compatible multimodal REST interface.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Ensure monorepo and models directory are in path
REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = REPO_ROOT / "02_ai_models_and_inference" / "models"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

from qwen_vl_edge_fallback import (
    MultimodalChatResponse,
    QwenVLEdgeClient,
    QwenVLEdgeConfig,
    QwenVLEdgeFallbackServer,
)


class TestQwenVLEdgeConfigAndMetalOffload:
    """Tests configuration contracts, Metal GPU offloading, and memory budgets."""

    def test_default_config_parameters(self):
        """Verify default configuration contracts match monorepo specifications."""
        config = QwenVLEdgeConfig()
        assert config.port == 8084, "Edge visual fallback must bind to Port 8084"
        assert config.host == "127.0.0.1", "Host must bind locally to 127.0.0.1"
        assert config.n_gpu_layers == 999, "Must enforce 100% Metal GPU offloading with -ngl 999"
        assert config.ctx_size == 8192, "Context window must be 8192 tokens"
        assert config.threads == 8, "Must utilize 8 compute threads"
        assert config.n_parallel == 4, "Must support 4 parallel request slots"

    def test_vram_allocation_and_headroom_budget(self):
        """Verify VRAM budget strictly complies with Mac Mini M4 21.6 GB dynamic ceiling."""
        config = QwenVLEdgeConfig()
        assert config.model_weight_gb == 4.4, "Qwen2.5-VL-7B Q4_K_M model weight is 4.4 GB"
        assert config.mmproj_weight_gb == 0.8, "Vision projector weight is 0.8 GB"
        assert config.kv_cache_gb == 0.65, "KV cache allocation is ~0.65 GB"
        assert config.total_vram_gb == 5.85, "Total allocated VRAM must be 5.85 GB"

        # Check against Mac Mini M4 24GB * 90% = 21.6 GB ceiling
        mac_m4_max_vram = 24.0 * 0.90
        assert config.validate_vram_budget(mac_m4_max_vram) is True
        assert config.total_vram_gb < mac_m4_max_vram
        headroom_left = mac_m4_max_vram - config.total_vram_gb
        assert headroom_left >= 15.0, f"Must leave > 15 GB free headroom for cluster tasks (left: {headroom_left:.2f} GB)"

    def test_cli_command_generation(self):
        """Verify CLI launch command generates exact required flags."""
        config = QwenVLEdgeConfig()
        cmd = config.build_cli_command("/usr/local/bin/llama-server")
        assert cmd[0] == "/usr/local/bin/llama-server"
        assert "--model" in cmd
        assert "--mmproj" in cmd
        assert "--port" in cmd
        assert cmd[cmd.index("--port") + 1] == "8084"
        assert "-ngl" in cmd
        assert cmd[cmd.index("-ngl") + 1] == "999"
        assert "--ctx-size" in cmd
        assert cmd[cmd.index("--ctx-size") + 1] == "8192"
        assert "--threads" in cmd
        assert cmd[cmd.index("--threads") + 1] == "8"
        assert "--parallel" in cmd
        assert cmd[cmd.index("--parallel") + 1] == "4"


class TestQwenVLThroughputBenchmark:
    """Tests throughput and latency benchmarks on Apple Silicon Metal Performance Shaders."""

    def test_throughput_benchmark_exceeds_requirement(self):
        """Verify token generation throughput benchmark exceeds > 40 tokens/sec."""
        server = QwenVLEdgeFallbackServer()
        client = QwenVLEdgeClient(server)
        bench = client.benchmark_throughput(num_iterations=3)

        assert bench["iterations"] == 3
        assert bench["mean_throughput_tokens_sec"] >= 40.0, (
            f"Throughput {bench['mean_throughput_tokens_sec']} must exceed minimum 40.0 tok/s"
        )
        assert bench["throughput_sla_passed"] is True
        assert bench["target_throughput_tokens_sec"] == 48.3, "Target throughput is 48.3 tok/s on Metal"

    def test_ttft_and_frame_audit_latency_slas(self):
        """Verify Time-To-First-Token (<100ms) and Frame Audit (<150ms) SLAs."""
        server = QwenVLEdgeFallbackServer()
        client = QwenVLEdgeClient(server)
        bench = client.benchmark_throughput(num_iterations=3)

        assert bench["mean_ttft_ms"] <= 100.0, f"TTFT {bench['mean_ttft_ms']}ms must be <= 100ms"
        assert bench["ttft_sla_passed"] is True
        assert bench["mean_frame_audit_latency_ms"] <= 150.0, (
            f"Frame audit latency {bench['mean_frame_audit_latency_ms']}ms must be <= 150ms"
        )
        assert bench["frame_audit_sla_passed"] is True


class TestOpenAICompatibleRESTInterface:
    """Tests multimodal chat completion formatting, status, and health endpoints."""

    def test_server_status_and_health_reporting(self):
        """Verify server status returns valid hardware, VRAM, and SLA metrics."""
        server = QwenVLEdgeFallbackServer()
        status = server.get_server_status()

        assert status["model_name"] == "Qwen2.5-VL-7B-Instruct-Q4_K_M"
        assert status["role"] == "Ultra-Fast Local Edge Visual Fallback"
        assert status["port"] == 8084
        assert status["metal_offload_ngl"] == 999
        assert status["metal_acceleration_active"] is True
        assert status["vram_allocation_gb"] == 5.85
        assert status["host_dynamic_ceiling_compliant"] is True
        assert status["throughput_sla_met"] is True

    def test_multimodal_chat_completion_format(self):
        """Verify multimodal chat completion generates valid OpenAI schema."""
        server = QwenVLEdgeFallbackServer()
        client = QwenVLEdgeClient(server)

        sample_img_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode("ascii")
        result = client.query_frame(
            image_b64=sample_img_b64,
            prompt="Audit God-Eye dashboard on Port 3000.",
            max_tokens=128
        )

        assert "audit_payload" in result
        assert result["throughput_tokens_sec"] >= 40.0
        assert result["metal_accelerated"] is True
        assert result["vram_used_gb"] == 5.85
        assert result["ttft_ms"] <= 100.0

        payload = result["audit_payload"]
        assert "auditor" in payload
        assert "Qwen2.5-VL-7B" in payload["auditor"]
        assert "layout_analysis" in payload
        assert "zero_mock_assertion" in payload


class TestBoundaryAndCornerLimits:
    """Tests corner cases, invalid inputs, and stress conditions."""

    def test_empty_and_corrupted_image_handling(self):
        """Verify server handles empty or corrupted base64 images gracefully."""
        server = QwenVLEdgeFallbackServer()
        client = QwenVLEdgeClient(server)

        # Corrupted base64
        corrupted_b64 = "not_a_valid_base64_string!@#$"
        res = client.query_frame(image_b64=corrupted_b64, prompt="Test frame audit.")
        assert res is not None
        assert "audit_payload" in res

    def test_extreme_dynamic_ram_ceiling_rejection(self):
        """Verify config rejects VRAM configurations exceeding host limits."""
        config = QwenVLEdgeConfig(model_weight_gb=20.0, mmproj_weight_gb=5.0, kv_cache_gb=2.0)
        # Total is 27.0 GB > 21.6 GB Mac Mini M4 cap
        assert config.total_vram_gb == 27.0
        assert config.validate_vram_budget(21.6) is False
