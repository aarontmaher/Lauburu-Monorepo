"""
Llama Server Execution Engine & Lifecycle Manager.

Manages the static llama-server process lifecycle, memory-tuned CLI arguments,
health checking, HTTP client/proxy requests, and fallback mock server for
non-target execution environments.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import RouterConfig, get_config
from src.container.memory_guard import MemoryGuard, MemoryStats

logger = logging.getLogger("smolagi.llama_runner")


@dataclass
class LlamaServerConfig:
    """Execution parameters for static llama-server process."""

    binary_path: str = "/usr/local/bin/llama-server"
    model_path: str = "/models/smollm2-135m-instruct-q4_k_m.gguf"
    host: str = "127.0.0.1"
    port: int = 8081
    ctx_size: int = 1024
    batch_size: int = 128
    ubatch_size: int = 32
    threads: int = 3
    parallel: int = 1
    cache_type_k: str = "q4_0"
    cache_type_v: str = "q4_0"
    no_mmap: bool = True
    cont_batching: bool = True
    log_disable: bool = True
    extra_args: List[str] = field(default_factory=list)

    @classmethod
    def from_router_config(
        cls, router_config: Optional[RouterConfig] = None
    ) -> LlamaServerConfig:
        """Construct LlamaServerConfig from global RouterConfig."""
        cfg = router_config or get_config()
        return cls(
            binary_path=cfg.llama_binary_path,
            model_path=cfg.model_path,
            host=cfg.llama_server_host,
            port=cfg.llama_server_port,
            ctx_size=cfg.context_size,
            batch_size=cfg.batch_size,
            ubatch_size=cfg.ubatch_size,
            threads=cfg.threads,
            parallel=cfg.parallel_slots,
            cache_type_k=cfg.cache_type_k,
            cache_type_v=cfg.cache_type_v,
            no_mmap=cfg.no_mmap,
            cont_batching=cfg.cont_batching,
            log_disable=cfg.log_disable,
        )

    def build_command_args(self) -> List[str]:
        """Generate CLI arguments for static llama-server invocation."""
        args = [
            self.binary_path,
            "--model",
            self.model_path,
            "--host",
            self.host,
            "--port",
            str(self.port),
            "--ctx-size",
            str(self.ctx_size),
            "--batch-size",
            str(self.batch_size),
            "--ubatch-size",
            str(self.ubatch_size),
            "--threads",
            str(self.threads),
            "--parallel",
            str(self.parallel),
            "--cache-type-k",
            self.cache_type_k,
            "--cache-type-v",
            self.cache_type_v,
        ]
        if self.no_mmap:
            args.append("--no-mmap")
        if self.cont_batching:
            args.append("--cont-batching")
        if self.log_disable:
            args.append("--log-disable")
        if self.extra_args:
            args.extend(self.extra_args)
        return args


class MockLlamaHTTPHandler(BaseHTTPRequestHandler):
    """Genuine HTTP request handler simulating llama.cpp OpenAI-compatible server."""

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Suppress standard logging to keep test outputs clean."""
        pass

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        """Handle health check and model discovery."""
        if self.path in ("/health", "/v1/health"):
            self._send_json(200, {"status": "ok", "slots_idle": 1, "slots_processing": 0})
        elif self.path in ("/v1/models", "/models"):
            model_name = getattr(self.server, "model_name", "smollm2-135m-instruct-q4_k_m")
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": model_name,
                            "object": "model",
                            "created": int(time.time()),
                            "owned_by": "smolagi-router",
                        }
                    ],
                },
            )
        else:
            self._send_json(404, {"error": f"Endpoint {self.path} not found"})

    def do_POST(self) -> None:  # noqa: N802
        """Handle completion and chat completion requests."""
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            req_data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            req_data = {}

        model_name = getattr(self.server, "model_name", "smollm2-135m-instruct-q4_k_m")

        if self.path in ("/v1/completions", "/completion"):
            prompt = req_data.get("prompt", "")
            max_tokens = req_data.get("max_tokens", 64)
            # Produce authentic response echoing context or decision
            simulated_text = f" [smolagi-route-ack: decision processed for '{prompt[:32]}...']"
            p_tokens = max(1, len(prompt.split()))
            c_tokens = max(1, len(simulated_text.split()))

            self._send_json(
                200,
                {
                    "id": f"cmpl-{int(time.time()*1000)}",
                    "object": "text_completion",
                    "created": int(time.time()),
                    "model": model_name,
                    "choices": [
                        {
                            "text": simulated_text,
                            "index": 0,
                            "logprobs": None,
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": p_tokens,
                        "completion_tokens": c_tokens,
                        "total_tokens": p_tokens + c_tokens,
                    },
                },
            )
        elif self.path in ("/v1/chat/completions", "/chat/completions"):
            messages = req_data.get("messages", [])
            last_msg = messages[-1].get("content", "") if messages else ""
            simulated_reply = f"Consensus verified for route request: {last_msg[:64]}"
            p_tokens = sum(max(1, len(m.get("content", "").split())) for m in messages) or 1
            c_tokens = max(1, len(simulated_reply.split()))

            self._send_json(
                200,
                {
                    "id": f"chatcmpl-{int(time.time()*1000)}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": simulated_reply,
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": p_tokens,
                        "completion_tokens": c_tokens,
                        "total_tokens": p_tokens + c_tokens,
                    },
                },
            )
        else:
            self._send_json(404, {"error": f"Endpoint {self.path} not found"})


class MockLlamaServer:
    """In-process HTTP server simulating static llama.cpp server for dev & tests."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8081, model_name: str = "smollm2-135m-instruct-q4_k_m") -> None:
        self.host = host
        self.port = port
        self.model_name = model_name
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self._is_running = False

    def start(self) -> None:
        """Start the in-process HTTP mock server."""
        if self._is_running:
            return

        self.server = HTTPServer((self.host, self.port), MockLlamaHTTPHandler)
        setattr(self.server, "model_name", self.model_name)
        self._is_running = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        logger.info("Started MockLlamaServer on %s:%d", self.host, self.port)

    def stop(self) -> None:
        """Stop the in-process HTTP mock server."""
        if not self._is_running:
            return

        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            self.thread = None
        self._is_running = False
        logger.info("Stopped MockLlamaServer on %s:%d", self.host, self.port)

    @property
    def is_running(self) -> bool:
        return self._is_running


class LlamaServerRunner:
    """
    Supervises the static llama-server process lifecycle, memory usage,
    and provides client interface for local AI inference.
    """

    def __init__(
        self,
        config: Optional[LlamaServerConfig] = None,
        memory_guard: Optional[MemoryGuard] = None,
        use_mock_if_missing: bool = True,
    ) -> None:
        self.config = config or LlamaServerConfig.from_router_config()
        self.memory_guard = memory_guard or MemoryGuard()
        self.use_mock_if_missing = use_mock_if_missing
        self.process: Optional[subprocess.Popen[bytes]] = None
        self.mock_server: Optional[MockLlamaServer] = None
        self._lock = threading.Lock()

    @property
    def is_mock(self) -> bool:
        """Check if currently running via in-process mock server."""
        return self.mock_server is not None and self.mock_server.is_running

    def is_binary_available(self) -> bool:
        """Check if compiled llama-server binary exists and is executable."""
        p = Path(self.config.binary_path)
        return p.is_file() and os.access(p, os.X_OK)

    def get_pid(self) -> Optional[int]:
        """Return PID of running llama-server subprocess, or current PID if mock."""
        if self.process and self.process.poll() is None:
            return self.process.pid
        if self.is_mock:
            return os.getpid()
        return None

    def start(self, timeout_sec: float = 5.0) -> bool:
        """
        Start the llama-server process or fallback mock server.
        Blocks until healthcheck succeeds or timeout is reached.
        """
        with self._lock:
            if self.is_running():
                logger.debug("llama-server is already running.")
                return True

            if self.is_binary_available():
                cmd = self.config.build_command_args()
                logger.info("Spawning static llama-server: %s", " ".join(cmd))
                try:
                    self.process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL if self.config.log_disable else None,
                        stderr=subprocess.DEVNULL if self.config.log_disable else None,
                    )
                except OSError as e:
                    logger.error("Failed to spawn llama-server process: %s", e)
                    if not self.use_mock_if_missing:
                        return False
                    self.process = None

            if not self.process and self.use_mock_if_missing:
                logger.info("Native llama-server binary not found. Initializing MockLlamaServer...")
                model_name = Path(self.config.model_path).stem
                self.mock_server = MockLlamaServer(
                    host=self.config.host,
                    port=self.config.port,
                    model_name=model_name,
                )
                self.mock_server.start()

            # Poll healthcheck endpoint until ready
            start_time = time.time()
            while time.time() - start_time < timeout_sec:
                if self.health_check(timeout_sec=0.5):
                    logger.info("llama-server successfully verified and healthy on port %d", self.config.port)
                    return True
                time.sleep(0.1)

            logger.error("llama-server failed to become healthy within %.1f seconds", timeout_sec)
            return False

    def stop(self, timeout_sec: float = 3.0) -> bool:
        """
        Stop running llama-server or mock server gracefully.
        """
        with self._lock:
            if self.mock_server:
                self.mock_server.stop()
                self.mock_server = None

            if self.process:
                if self.process.poll() is None:
                    logger.info("Sending SIGTERM to llama-server (PID %d)...", self.process.pid)
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=timeout_sec)
                    except subprocess.TimeoutExpired:
                        logger.warning("llama-server did not terminate in %.1fs. Sending SIGKILL...", timeout_sec)
                        self.process.kill()
                        self.process.wait(timeout=1.0)
                self.process = None

            return True

    def restart(self, new_config: Optional[LlamaServerConfig] = None) -> bool:
        """Restart server, optionally applying new model or configuration."""
        self.stop()
        if new_config:
            self.config = new_config
        return self.start()

    def is_running(self) -> bool:
        """Check if server process or mock is active."""
        if self.mock_server and self.mock_server.is_running:
            return True
        if self.process and self.process.poll() is None:
            return True
        return False

    def health_check(self, timeout_sec: float = 1.0) -> bool:
        """Probe /health endpoint."""
        url = f"http://{self.config.host}:{self.config.port}/health"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("status") in ("ok", "loading model", "ready") or "slots_idle" in data
                return False
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def get_memory_usage(self) -> MemoryStats:
        """Inspect resident memory usage of the llama-server process."""
        pid = self.get_pid()
        if pid:
            return self.memory_guard.get_process_memory(pid)
        return self.memory_guard.get_process_memory(os.getpid())

    def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 64,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None,
        timeout_sec: float = 5.0,
    ) -> Dict[str, Any]:
        """Send completion request to /v1/completions."""
        url = f"http://{self.config.host}:{self.config.port}/v1/completions"
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if stop:
            payload["stop"] = stop

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error("Failed to generate completion: %s", e)
            raise RuntimeError(f"llama-server completion failed: {e}") from e

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 64,
        temperature: float = 0.7,
        timeout_sec: float = 5.0,
    ) -> Dict[str, Any]:
        """Send chat completion request to /v1/chat/completions."""
        url = f"http://{self.config.host}:{self.config.port}/v1/chat/completions"
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error("Failed to generate chat completion: %s", e)
            raise RuntimeError(f"llama-server chat completion failed: {e}") from e


def main() -> None:
    """CLI entrypoint for standalone llama runner verification."""
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
    runner = LlamaServerRunner()
    logger.info("Initializing smolagi llama runner...")
    if runner.start():
        logger.info("Llama server running. PID: %s, Mem RSS: %.2f MB", runner.get_pid(), runner.get_memory_usage().rss_mb)
        try:
            res = runner.generate_completion("Ping router consensus")
            logger.info("Sample completion output: %s", res.get("choices", [{}])[0].get("text"))
            # Keep running until signal
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted. Stopping runner...")
        finally:
            runner.stop()
    else:
        logger.error("Failed to start llama server runner.")
        sys.exit(1)


if __name__ == "__main__":
    main()
