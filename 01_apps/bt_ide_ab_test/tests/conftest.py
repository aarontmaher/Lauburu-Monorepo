"""
tests/conftest.py
Global pytest fixtures and mock loopback HTTP servers for the IDE Intelligence Architecture.

Simulates:
1. Multi-IP telemetry endpoints across all 7 mesh layers.
2. Mock local LLM endpoints:
   - Port 8081: Subordinate Syntax Worker (Qwen 2.5 Coder 7B) with SSE streaming & standard completions.
   - Port 8082: Sovereign Master Local Orchestrator (Qwen 3.8 Max / Hermes 3 tool router).
3. Mock Vector DB (Qdrant REST on Port 6333).
4. Mock Cloud API (OpenRouter / Gemini Pro) with zero-leakage inspection interceptors.
"""

import os
import sys
import time
import json
import socket
import threading
import tempfile
import shutil
from typing import Dict, Any, List, Optional, Tuple
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def find_free_port() -> int:
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class MockServerThread:
    """Helper to run a mock HTTPServer in a daemon thread."""
    def __init__(self, handler_cls, port: Optional[int] = None):
        self.port = port if port is not None else find_free_port()
        self.server = HTTPServer(('127.0.0.1', self.port), handler_cls)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.handler_cls = handler_cls

    def start(self):
        self.thread.start()
        time.sleep(0.05)
        return self

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass


class MockTelemetryHandler(BaseHTTPRequestHandler):
    """
    Mock OS telemetry endpoint simulating Darwin sysctl/vm_stat or Linux /proc/meminfo.
    """
    # Shared state across instances of this handler
    node_id: str = "node_default"
    total_ram_mb: float = 16384.0
    free_ram_mb: float = 8192.0
    available_ram_mb: float = 12288.0
    utilization_pct: float = 25.0
    dynamic_safety_threshold_mb: float = 3276.8
    is_saturated: bool = False
    is_healthy: bool = True
    delay_sec: float = 0.0
    status_code: int = 200
    custom_payload: Optional[dict] = None
    request_log: List[dict] = []

    def log_message(self, format, *args):
        # Silence default stderr logging
        pass

    def do_GET(self):
        if self.delay_sec > 0:
            time.sleep(self.delay_sec)

        MockTelemetryHandler.request_log.append({
            "path": self.path,
            "method": "GET",
            "headers": dict(self.headers)
        })

        if not self.is_healthy or self.status_code != 200:
            self.send_response(self.status_code)
            self.end_headers()
            self.wfile.write(b'{"error": "Simulated node telemetry failure"}')
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        payload = self.custom_payload or {
            "node_id": self.node_id,
            "total_ram_mb": self.total_ram_mb,
            "free_ram_mb": self.free_ram_mb,
            "available_ram_mb": self.available_ram_mb,
            "utilization_pct": self.utilization_pct,
            "dynamic_safety_threshold_mb": self.dynamic_safety_threshold_mb,
            "is_saturated": self.is_saturated,
            "is_reachable": True
        }
        self.wfile.write(json.dumps(payload).encode("utf-8"))


class MockCoderHandler(BaseHTTPRequestHandler):
    """
    Mock Port 8081: Subordinate Syntax Worker (Qwen 2.5 Coder 7B).
    Supports regular completions and streaming SSE.
    """
    call_log: List[dict] = []
    response_text: str = "def solve_matrix(a, b):\n    return [1, 2, 3]"

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            body = {"raw": body_bytes.decode("utf-8", errors="ignore")}

        MockCoderHandler.call_log.append({
            "path": self.path,
            "headers": dict(self.headers),
            "body": body
        })

        # Check if streaming is requested
        stream = body.get("stream", False)
        if stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            
            tokens = self.response_text.split()
            for token in tokens:
                chunk = {
                    "choices": [{
                        "delta": {"content": token + " "},
                        "finish_reason": None
                    }]
                }
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(0.01)
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "id": "cmpl-mock-qwen-coder",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "qwen2.5-coder-7b-instruct",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self.response_text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 15,
                    "completion_tokens": 20,
                    "total_tokens": 35
                }
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))


class MockHermesHandler(BaseHTTPRequestHandler):
    """
    Mock Port 8082: Sovereign Master Local Orchestrator (Qwen 3.8 Max / Hermes 3).
    Supports Hermes 3 tool parsing, XML tags, and routing logic.
    """
    call_log: List[dict] = []
    tool_call_response: Optional[dict] = None
    custom_content: Optional[str] = None

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            body = {"raw": body_bytes.decode("utf-8", errors="ignore")}

        MockHermesHandler.call_log.append({
            "path": self.path,
            "headers": dict(self.headers),
            "body": body
        })

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        # If tools were in the request, return tool call
        tools = body.get("tools", [])
        if tools or self.tool_call_response:
            tool_payload = self.tool_call_response or {
                "name": "vector_search",
                "arguments": {"query": "ecg_filter", "top_k": 3}
            }
            content = f"<tool_call>\n{json.dumps(tool_payload)}\n</tool_call>"
            resp = {
                "id": "chatcmpl-hermes-mock",
                "object": "chat.completion",
                "model": "qwen_38_max_abliterated",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self.custom_content or content,
                        "tool_calls": [{
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": tool_payload.get("name", "vector_search"),
                                "arguments": json.dumps(tool_payload.get("arguments", {}))
                            }
                        }]
                    },
                    "finish_reason": "tool_calls"
                }],
                "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75}
            }
        else:
            resp = {
                "id": "chatcmpl-hermes-mock",
                "object": "chat.completion",
                "model": "qwen_38_max_abliterated",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self.custom_content or "Hermes 3 Master Plan: executing task."
                    },
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45}
            }
        self.wfile.write(json.dumps(resp).encode("utf-8"))


class MockQdrantHandler(BaseHTTPRequestHandler):
    """
    Mock Port 6333: Qdrant Vector DB REST API.
    """
    call_log: List[dict] = []

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        MockQdrantHandler.call_log.append({"method": "GET", "path": self.path})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "result": {"collections": [{"name": "ide_codebase_context"}]}}).encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            body = {}

        MockQdrantHandler.call_log.append({"method": "POST", "path": self.path, "body": body})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        resp = {
            "result": [
                {
                    "id": "vec-1",
                    "score": 0.94,
                    "payload": {
                        "filepath": "01_apps/bt_ide_ab_test/core/ram_governor.py",
                        "snippet": "class MeshRAMGovernor:\n    def evaluate_global_pool(self): ...",
                        "metadata": {"layer": "L1", "category": "governor"}
                    }
                },
                {
                    "id": "vec-2",
                    "score": 0.88,
                    "payload": {
                        "filepath": "03_biometrics/pan_tompkins.py",
                        "snippet": "def pan_tompkins_qrs_detector(ecg_stream): ...",
                        "metadata": {"layer": "L3", "category": "dsp"}
                    }
                }
            ],
            "status": "ok",
            "time": 0.002
        }
        self.wfile.write(json.dumps(resp).encode("utf-8"))


class MockCloudHandler(BaseHTTPRequestHandler):
    """
    Mock Cloud Provider (OpenRouter / Gemini Pro) endpoint.
    Crucial for Rule 4 (Zero Auto-Cloud Leakage) verification.
    """
    call_log: List[dict] = []
    allow_requests: bool = True
    response_content: str = "Cloud Reasoning: 1. Refactor dependencies. 2. Verify invariance."

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            body = {"raw": body_bytes.decode("utf-8", errors="ignore")}

        MockCloudHandler.call_log.append({
            "path": self.path,
            "headers": dict(self.headers),
            "body": body,
            "timestamp": time.time()
        })

        if not self.allow_requests:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"error": "Cloud execution forbidden by mock"}')
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        resp = {
            "id": "chatcmpl-cloud-ultra",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "google/gemini-pro-1.5",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": self.response_content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 12500,
                "completion_tokens": 400,
                "total_tokens": 12900
            }
        }
        self.wfile.write(json.dumps(resp).encode("utf-8"))


@pytest.fixture(scope="function")
def reset_mock_logs():
    """Reset all mock call logs before each test."""
    MockTelemetryHandler.request_log.clear()
    MockTelemetryHandler.status_code = 200
    MockTelemetryHandler.delay_sec = 0.0
    MockTelemetryHandler.is_healthy = True
    MockTelemetryHandler.custom_payload = None

    MockCoderHandler.call_log.clear()
    MockHermesHandler.call_log.clear()
    MockHermesHandler.tool_call_response = None
    MockHermesHandler.custom_content = None

    MockQdrantHandler.call_log.clear()
    MockCloudHandler.call_log.clear()
    MockCloudHandler.allow_requests = True


@pytest.fixture(scope="session")
def mock_servers():
    """
    Spins up background mock HTTP servers on free ports for the entire test session.
    Returns dictionary with live URLs and server handles.
    """
    # Create handler subclasses with node-specific IDs
    def make_telemetry_server(node_id: str, total_mb: float, avail_mb: float, util: float):
        class NodeHandler(MockTelemetryHandler):
            pass
        NodeHandler.node_id = node_id
        NodeHandler.total_ram_mb = total_mb
        NodeHandler.available_ram_mb = avail_mb
        NodeHandler.free_ram_mb = avail_mb * 0.7
        NodeHandler.utilization_pct = util
        return MockServerThread(NodeHandler).start()

    servers = {
        "telemetry_L1": make_telemetry_server("L1_Mac_Host", 24576.0, 18432.0, 25.0),
        "telemetry_L2": make_telemetry_server("L2_MacBook_Pro", 16384.0, 12288.0, 25.0),
        "telemetry_L3": make_telemetry_server("L3_Linux_Hub", 16384.0, 13107.2, 20.0),
        "telemetry_L4": make_telemetry_server("L4_Linux_Tablet", 8192.0, 6144.0, 25.0),
        "telemetry_L5": make_telemetry_server("L5_MacBook_Air", 16384.0, 12288.0, 25.0),
        "telemetry_L6": make_telemetry_server("L6_Pixel_10_Edge", 16384.0, 13107.2, 20.0),
        "telemetry_L7": make_telemetry_server("L7_Samsung_S20", 12288.0, 9216.0, 25.0),
        "coder_8081": MockServerThread(MockCoderHandler).start(),
        "hermes_8082": MockServerThread(MockHermesHandler).start(),
        "qdrant_6333": MockServerThread(MockQdrantHandler).start(),
        "cloud_mock": MockServerThread(MockCloudHandler).start(),
    }

    yield servers

    # Teardown all servers
    for name, srv in servers.items():
        srv.stop()


@pytest.fixture(scope="function")
def isolated_workspace(tmp_path):
    """
    Creates an isolated temporary directory structured as a Lauburu workspace
    for testing SeaweedFS storage affinity and distillation queues without
    touching real storage volumes.
    """
    ws = tmp_path / "workspace"
    ws.mkdir()
    
    # Subdirectories
    (ws / "01_apps" / "bt_ide_ab_test").mkdir(parents=True)
    (ws / "04_data_and_memory" / "lora_datasets").mkdir(parents=True)
    (ws / "vector_db").mkdir(parents=True)
    (ws / ".git").mkdir(parents=True)
    
    # Sample files
    (ws / "01_apps" / "bt_ide_ab_test" / "main.py").write_text("# main entry point\n")
    (ws / "04_data_and_memory" / "lora_datasets" / "traces.jsonl").write_text('{"conversations": []}\n')
    (ws / "vector_db" / "embeddings.bin").write_bytes(b"\x00" * 64)
    
    return ws


@pytest.fixture
def sample_overflow_prompt():
    """Generates a prompt strictly guaranteed to exceed the 8,192 token ceiling."""
    # Approximate 1 token ~= 4 chars; 10,000 tokens ~= 40,000 chars
    return "def large_scale_analysis():\n" + ("    x = 42\n    # processing step\n" * 4000)


@pytest.fixture
def sample_code_prompt():
    """Standard short code prompt under 100 tokens."""
    return "def calculate_qrs_peaks(ecg_signal, sampling_rate=512):\n    pass"


@pytest.fixture
def sample_hermes_tools():
    """Sample Hermes 3 XML / JSON tool definitions."""
    return [
        {
            "type": "function",
            "function": {
                "name": "vector_search",
                "description": "Retrieve code context from Qdrant vector database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Query string"},
                        "top_k": {"type": "integer", "description": "Number of results"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_source_file",
                "description": "Read file contents from workspace",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Target relative file path"}
                    },
                    "required": ["filepath"]
                }
            }
        }
    ]
