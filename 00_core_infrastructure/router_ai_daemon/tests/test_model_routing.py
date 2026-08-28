"""
Unit and Integration Test Suite for Milestone M5:
Autonomous HuggingFace GGUF Discovery & Hot-Swap Engine.

Validates Features F10 and F11 and Interface Contract 4:
- HF Hub token auth, sub-1B GGUF discovery, RAM budget validation
- Chunked streaming downloader to tmpfs with SHA-256 verification and atomic staging
- Zero-downtime hot-swap proxy with in-memory request buffering and memory bounds
"""

import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
import urllib.error
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from src.config import RouterConfig
from src.container.llama_runner import LlamaServerConfig, LlamaServerRunner, MockLlamaServer
from src.container.memory_guard import MemoryGuard
from src.model_routing import (
    DiscoveredModel,
    DownloadResult,
    HFAuth,
    HFModelDiscovery,
    HotSwapProxy,
    ModelSwapResult,
    QueuedRequest,
    SafeModelDownloader,
    calculate_projected_ram_mb,
    extract_parameter_count,
    extract_quantization,
    get_hot_swap_proxy,
    hot_swap_model,
    validate_ram_budget,
)


# ===========================================================================
# 1. Hugging Face Authentication & Resolution Tests
# ===========================================================================

class TestHFAuthResolution:
    """Validates secure token handling and zero-flash-wear credential isolation."""

    def test_explicit_token_precedence(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HF_TOKEN", "env_token")
        secret_file = tmp_path / "hf_token"
        secret_file.write_text("file_token")

        resolved = HFAuth.resolve_token(explicit_token="explicit_tok", secrets_path=str(secret_file))
        assert resolved == "explicit_tok"

    def test_env_token_resolution(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HF_TOKEN", "env_token_12345")
        secret_file = tmp_path / "hf_token"
        secret_file.write_text("file_token")

        resolved = HFAuth.resolve_token(secrets_path=str(secret_file))
        assert resolved == "env_token_12345"

    def test_huggingface_hub_token_env_resolution(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.setenv("HUGGINGFACE_HUB_TOKEN", "hub_token_67890")

        resolved = HFAuth.resolve_token()
        assert resolved == "hub_token_67890"

    def test_tmpfs_secret_file_resolution(self, monkeypatch, tmp_path):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HUGGINGFACE_HUB_TOKEN", raising=False)
        secret_file = tmp_path / "hf_token"
        secret_file.write_text("tmpfs_file_token_secret\n")

        resolved = HFAuth.resolve_token(secrets_path=str(secret_file))
        assert resolved == "tmpfs_file_token_secret"

    def test_anonymous_public_fallback(self, monkeypatch, tmp_path):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HUGGINGFACE_HUB_TOKEN", raising=False)
        non_existent = tmp_path / "non_existent_token"

        resolved = HFAuth.resolve_token(secrets_path=str(non_existent))
        assert resolved is None

    def test_headers_with_and_without_token(self):
        hdr_auth = HFAuth.get_headers(token="secret_bearer_token")
        assert hdr_auth["Authorization"] == "Bearer secret_bearer_token"
        assert "SmolAGI-Router" in hdr_auth["User-Agent"]

        hdr_anon = HFAuth.get_headers(token=None)
        assert "Authorization" not in hdr_anon


# ===========================================================================
# 2. Sub-1B Model Metadata Extraction & Memory Budget Tests
# ===========================================================================

class TestHFModelDiscoveryAndMetadata:
    """Validates GGUF parsing heuristics and mathematical RAM projection."""

    def test_extract_quantization_heuristics(self):
        assert extract_quantization("SmolLM2-135M-Instruct-Q4_K_M.gguf") == "Q4_K_M"
        assert extract_quantization("qwen2.5-0.5b-instruct-iq2_xxs.gguf") == "IQ2_XXS"
        assert extract_quantization("deepseek-r1-distill-iq1_s.gguf") == "IQ1_S"
        assert extract_quantization("danube3-500m-chat-q8_0.gguf") == "Q8_0"
        assert extract_quantization("unknown-format.bin") == "UNKNOWN"

    def test_extract_parameter_count_heuristics(self):
        assert extract_parameter_count("SmolLM2-135M-Instruct-Q4_K_M.gguf") == "135M"
        assert extract_parameter_count("SmolLM2-360M-Instruct.gguf") == "360M"
        assert extract_parameter_count("qwen2.5-0.5b-instruct.gguf") == "0.5B"
        assert extract_parameter_count("deepseek-r1-distill-qwen-1.5b.gguf") == "1.5B"
        assert extract_parameter_count("llama-3.3-70b.gguf") == "70B"

    def test_calculate_projected_ram_formula(self):
        # 105.4 MB weights + 1.2 MB KV (2048 ctx) + 35 MB server + 20 MB daemon = ~161.6 MB
        ram = calculate_projected_ram_mb(105.4, context_len=2048)
        assert 160.0 <= ram <= 165.0

        # Larger weights (235 MB)
        ram_360m = calculate_projected_ram_mb(235.0, context_len=2048)
        assert 290.0 <= ram_360m <= 295.0

    def test_validate_ram_budget_boundaries(self):
        # Within limit (92 MB weight -> ~148 MB total <= 300 MB)
        assert validate_ram_budget(92.0, max_weight_mb=200.0, max_total_ram_mb=300.0) is True

        # Exceeds max weight constraint (201 MB > 200 MB)
        assert validate_ram_budget(201.0, max_weight_mb=200.0, max_total_ram_mb=300.0) is False

        # Exceeds total RAM budget
        assert validate_ram_budget(195.0, max_weight_mb=200.0, max_total_ram_mb=200.0) is False

    def test_curated_catalog_discovery_filtering(self):
        discovery = HFModelDiscovery()
        models = discovery.discover_models(architectures=["SmolLM2"])
        assert len(models) >= 2
        for m in models:
            assert "smollm2" in m.repo_id.lower() or "smollm2" in m.filename.lower()
            assert m.is_ram_compliant is True
            assert m.size_mb <= 200.0

    def test_quantization_filtering(self):
        discovery = HFModelDiscovery()
        models_iq2 = discovery.discover_models(quantizations=["IQ2_XXS"])
        assert len(models_iq2) >= 1
        for m in models_iq2:
            assert m.quantization == "IQ2_XXS"


# ===========================================================================
# 3. Safe Streaming Downloader Tests
# ===========================================================================

class TestSafeModelDownloader:
    """Validates tmpfs streaming, chunked processing, SHA-256 verification, and atomic rollback."""

    def test_verify_storage_headroom_success(self, tmp_path):
        downloader = SafeModelDownloader(target_dir=tmp_path)
        has_space, free_bytes, msg = downloader.verify_storage_headroom(1024 * 1024 * 10)  # 10MB
        assert has_space is True
        assert free_bytes > 0

    def test_verify_storage_headroom_insufficient(self, tmp_path, monkeypatch):
        downloader = SafeModelDownloader(target_dir=tmp_path)
        # Mock free bytes to 5MB
        mock_stat = MagicMock(f_bavail=1024, f_frsize=5120)  # 5MB
        monkeypatch.setattr(os, "statvfs", lambda p: mock_stat)

        has_space, free_bytes, msg = downloader.verify_storage_headroom(1024 * 1024 * 50)  # 50MB
        assert has_space is False
        assert "Insufficient storage headroom" in msg

    def test_filename_security_path_traversal_prevention(self, tmp_path):
        downloader = SafeModelDownloader(target_dir=tmp_path)
        with pytest.raises(ValueError, match="directory components not allowed"):
            downloader.download_model("http://example.com/model.gguf", "../../../etc/shadow")

    def test_streaming_download_with_sha256_verification_success(self, tmp_path):
        downloader = SafeModelDownloader(target_dir=tmp_path, chunk_size=1024)
        
        test_data = b"GGUF_AUTHENTIC_WEIGHT_STREAM_DATA_" * 1000
        expected_sha = hashlib.sha256(test_data).hexdigest()

        # Mock urllib response
        mock_resp = MagicMock()
        mock_resp.headers.get.return_value = str(len(test_data))
        # Deliver chunks
        chunks = [test_data[i:i+1024] for i in range(0, len(test_data), 1024)] + [b""]
        mock_resp.read.side_effect = chunks
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = downloader.download_model(
                url="https://huggingface.co/unsloth/SmolLM2-135M/resolve/main/model.gguf",
                filename="smollm2-135m.gguf",
                expected_sha256=expected_sha,
            )

        assert res.success is True
        assert res.size_bytes == len(test_data)
        assert res.sha256 == expected_sha
        target_file = tmp_path / "smollm2-135m.gguf"
        assert target_file.is_file()
        assert target_file.read_bytes() == test_data

        # Verify staging file is cleaned up
        staging_file = tmp_path / "smollm2-135m.gguf.download.tmp"
        assert not staging_file.exists()

    def test_sha256_checksum_mismatch_triggers_rollback(self, tmp_path):
        downloader = SafeModelDownloader(target_dir=tmp_path, chunk_size=1024)
        
        corrupted_data = b"CORRUPTED_PAYLOAD_DATA_BYTES"
        wrong_expected_sha = "0" * 64

        mock_resp = MagicMock()
        mock_resp.headers.get.return_value = str(len(corrupted_data))
        mock_resp.read.side_effect = [corrupted_data, b""]
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(ValueError, match="SHA-256 Checksum verification failed"):
                downloader.download_model(
                    url="https://huggingface.co/corrupt/model.gguf",
                    filename="corrupt_model.gguf",
                    expected_sha256=wrong_expected_sha,
                )

        # Ensure target file not created and temporary staging file purged
        target_file = tmp_path / "corrupt_model.gguf"
        staging_file = tmp_path / "corrupt_model.gguf.download.tmp"
        assert not target_file.exists()
        assert not staging_file.exists()

    def test_max_size_bytes_boundary_enforcement(self, tmp_path):
        downloader = SafeModelDownloader(target_dir=tmp_path)
        
        # Content-length indicates 500MB (exceeds 200MB budget)
        mock_resp = MagicMock()
        mock_resp.headers.get.return_value = str(500 * 1024 * 1024)
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(ValueError, match="exceeds maximum allowed"):
                downloader.download_model(
                    url="https://huggingface.co/oversized/model.gguf",
                    filename="oversized.gguf",
                    max_size_bytes=200 * 1024 * 1024,
                )


# ===========================================================================
# 4. Zero-Downtime Hot-Swap Proxy & Request Queueing Tests
# ===========================================================================

class TestHotSwapProxy:
    """Validates in-process request buffering, zero dropped requests, SLA timing, and memory bounds."""

    @pytest.fixture
    def setup_proxy(self, tmp_path):
        """Build an isolated HotSwapProxy instance with mock llama server and temp models directory."""
        models_dir = tmp_path / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dummy existing model
        init_model = models_dir / "smollm2-135m-instruct-q4_k_m.gguf"
        init_model.write_bytes(b"GGUF_MODEL_INIT_BYTES" * 100)

        cfg = RouterConfig(
            tmpfs_models_dir=str(models_dir),
            model_path=str(init_model),
            llama_server_port=8188,  # Isolated dynamic port
        )
        runner = LlamaServerRunner(config=LlamaServerConfig.from_router_config(cfg), use_mock_if_missing=True)
        runner.start(timeout_sec=3.0)

        downloader = SafeModelDownloader(target_dir=models_dir, config=cfg)
        discovery = HFModelDiscovery(config=cfg)
        memory_guard = MemoryGuard(config=cfg)

        proxy = HotSwapProxy(
            runner=runner,
            memory_guard=memory_guard,
            downloader=downloader,
            discovery=discovery,
            config=cfg,
        )

        yield proxy

        # Cleanup
        proxy.runner.stop()

    def test_direct_inference_execution_when_idle(self, setup_proxy):
        proxy = setup_proxy
        res = proxy.generate_completion("Test routing decision prompt", max_tokens=16)
        assert "choices" in res
        assert len(res["choices"]) > 0

        chat_res = proxy.generate_chat_completion([{"role": "user", "content": "Ping router"}])
        assert "choices" in chat_res
        assert "assistant" in chat_res["choices"][0]["message"]["role"]

    def test_request_buffering_and_zero_dropped_requests_during_swap(self, setup_proxy, tmp_path):
        proxy = setup_proxy
        target_model = tmp_path / "models" / "smollm2-360m-instruct-iq2_xxs.gguf"
        target_model.write_bytes(b"GGUF_MODEL_360M_BYTES" * 100)

        responses = []
        threads = []

        def worker_req(req_id: int):
            try:
                r = proxy.generate_completion(f"Prompt from worker {req_id}", max_tokens=8, timeout_sec=6.0)
                responses.append((req_id, r, None))
            except Exception as e:
                responses.append((req_id, None, e))

        # Launch model swap in a background thread
        swap_result_holder = []

        def do_swap():
            res = proxy.hot_swap_model(
                repo_id="unsloth/SmolLM2-360M-Instruct-GGUF",
                filename="smollm2-360m-instruct-iq2_xxs.gguf",
                ram_budget_mb=300.0,
            )
            swap_result_holder.append(res)

        # Dispatch 5 client requests concurrently right as swap begins
        swap_thread = threading.Thread(target=do_swap)
        swap_thread.start()
        time.sleep(0.02)  # Give swap chance to enter swapping state

        for i in range(5):
            t = threading.Thread(target=worker_req, args=(i,))
            threads.append(t)
            t.start()

        swap_thread.join(timeout=10.0)
        for t in threads:
            t.join(timeout=10.0)

        # Verify swap outcome
        assert len(swap_result_holder) == 1
        swap_res = swap_result_holder[0]
        assert swap_res.success is True
        assert swap_res.active_model == "smollm2-360m-instruct-iq2_xxs"
        assert swap_res.swap_duration_ms < 2000.0  # Well within test tolerance

        # Verify all 5 requests completed with zero exceptions / 0 dropped
        assert len(responses) == 5
        for req_id, resp, err in responses:
            assert err is None, f"Worker {req_id} encountered error: {err}"
            assert resp is not None
            assert "choices" in resp

    def test_peak_memory_bounds_during_swap(self, setup_proxy, tmp_path):
        proxy = setup_proxy
        new_model = tmp_path / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
        new_model.write_bytes(b"GGUF_QWEN_500M_BYTES" * 100)

        swap_res = proxy.hot_swap_model(
            repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
            filename="qwen2.5-0.5b-instruct-q4_k_m.gguf",
            ram_budget_mb=300.0,
        )

        assert swap_res.success is True
        assert swap_res.peak_rss_mb <= 300.0
        assert swap_res.peak_rss_mb <= 216.0  # Strict target check

    def test_swap_rejection_on_ram_budget_violation(self, setup_proxy, tmp_path):
        proxy = setup_proxy
        oversized = tmp_path / "models" / "llama-3.3-70b.gguf"
        # 400MB mock file
        oversized.write_bytes(b"0" * (400 * 1024 * 1024))

        swap_res = proxy.hot_swap_model(
            repo_id="meta-llama/Llama-3.3-70B-GGUF",
            filename="llama-3.3-70b.gguf",
            ram_budget_mb=300.0,
        )

        assert swap_res.success is False
        assert "exceeds allowable RAM budget" in (swap_res.error_message or "")

    def test_hot_swap_model_contract_function(self, setup_proxy, monkeypatch):
        """Validates contract 4 hot_swap_model module export."""
        proxy = setup_proxy
        monkeypatch.setattr("src.model_routing.hot_swap_proxy.get_hot_swap_proxy", lambda: proxy)

        res = hot_swap_model("unsloth/SmolLM2-135M-Instruct-GGUF", "smollm2-135m-instruct-q4_k_m.gguf")
        assert isinstance(res, ModelSwapResult)
        assert res.success is True
