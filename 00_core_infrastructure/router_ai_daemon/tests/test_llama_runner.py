"""Unit tests for smolagi LlamaServerRunner and MockLlamaServer."""

import time
import pytest
from src.config import RouterConfig
from src.container.llama_runner import (
    LlamaServerConfig,
    LlamaServerRunner,
    MockLlamaServer,
)


def test_llama_server_config_build_command_args():
    """Verify CLI arguments generator builds all mandatory flags for 300MB bound."""
    config = LlamaServerConfig(
        binary_path="/usr/local/bin/llama-server",
        model_path="/models/smollm2-135m-instruct-q4_k_m.gguf",
        host="127.0.0.1",
        port=8081,
        ctx_size=1024,
        batch_size=128,
        ubatch_size=32,
        threads=3,
        parallel=1,
        cache_type_k="q4_0",
        cache_type_v="q4_0",
        no_mmap=True,
        cont_batching=True,
        log_disable=True,
    )
    args = config.build_command_args()
    assert args[0] == "/usr/local/bin/llama-server"
    assert "--model" in args
    assert "/models/smollm2-135m-instruct-q4_k_m.gguf" in args
    assert "--host" in args and "127.0.0.1" in args
    assert "--port" in args and "8081" in args
    assert "--ctx-size" in args and "1024" in args
    assert "--batch-size" in args and "128" in args
    assert "--ubatch-size" in args and "32" in args
    assert "--threads" in args and "3" in args
    assert "--parallel" in args and "1" in args
    assert "--cache-type-k" in args and "q4_0" in args
    assert "--cache-type-v" in args and "q4_0" in args
    assert "--no-mmap" in args
    assert "--cont-batching" in args
    assert "--log-disable" in args


def test_mock_llama_server_endpoints():
    """Verify in-process mock server provides authentic OpenAI/llama.cpp responses."""
    server = MockLlamaServer(host="127.0.0.1", port=18081, model_name="smollm2-135m")
    try:
        server.start()
        assert server.is_running is True

        cfg = LlamaServerConfig(host="127.0.0.1", port=18081)
        runner = LlamaServerRunner(config=cfg, use_mock_if_missing=False)

        # Health check
        assert runner.health_check(timeout_sec=2.0) is True

        # Completion
        resp = runner.generate_completion(prompt="Route decision for 192.168.8.230")
        assert "choices" in resp
        assert len(resp["choices"]) > 0
        assert "text" in resp["choices"][0]
        assert "usage" in resp

        # Chat completion
        chat_resp = runner.generate_chat_completion(
            messages=[{"role": "user", "content": "Ping router"}]
        )
        assert "choices" in chat_resp
        assert "message" in chat_resp["choices"][0]
        assert "content" in chat_resp["choices"][0]["message"]
    finally:
        server.stop()
        assert server.is_running is False


def test_llama_runner_lifecycle_and_restart():
    """Verify start, running state, restart, and stop on LlamaServerRunner."""
    cfg = LlamaServerConfig(host="127.0.0.1", port=18082)
    runner = LlamaServerRunner(config=cfg, use_mock_if_missing=True)

    try:
        started = runner.start(timeout_sec=3.0)
        assert started is True
        assert runner.is_running() is True
        assert runner.health_check() is True

        # Memory usage check
        mem = runner.get_memory_usage()
        assert mem.rss_mb > 0

        # Restart
        restarted = runner.restart()
        assert restarted is True
        assert runner.is_running() is True
    finally:
        runner.stop()
        assert runner.is_running() is False
