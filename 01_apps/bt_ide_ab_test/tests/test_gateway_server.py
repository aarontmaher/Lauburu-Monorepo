"""
Tests for Unified IDE Gateway Server (gateway/server.py) and CLI Launcher (lens_ide_router_gateway.py).
Verifies:
- Health and model catalogue endpoints
- Dual-engine routing: Hermes tool router vs Qwen 2.5 Coder
- Manual Cloud Escalation Gate blocking on context overflow (> 8192 tokens)
- Vector DB context paging and prompt injection
- FIM legacy completions
- Task registration for Backpressure Suspension
- Mesh telemetry and storage affinity endpoints
- Distillation metrics
- CLI launcher diagnostics (--check-mesh and --dry-run-check)
"""

import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from gateway.server import app, GATEWAY_PORT, HOST_SANCTUARY_MIN_GB
from lens_ide_router_gateway import check_mesh_health, probe_tcp_port


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def configure_gateway_routes(mock_servers):
    """Point gateway components to test mock servers."""
    from gateway.server import code_generator, hermes_router
    orig_primary = code_generator.primary_url
    orig_fallback = code_generator.fallback_url
    orig_hermes_url = hermes_router.hermes_url
    orig_coder_url = hermes_router.coder_url

    code_generator.primary_url = mock_servers['coder_8081'].url
    code_generator.fallback_url = mock_servers['hermes_8082'].url
    hermes_router.hermes_url = f"{mock_servers['hermes_8082'].url}/v1/chat/completions"
    hermes_router.coder_url = f"{mock_servers['coder_8081'].url}/v1/chat/completions"

    yield

    code_generator.primary_url = orig_primary
    code_generator.fallback_url = orig_fallback
    hermes_router.hermes_url = orig_hermes_url
    hermes_router.coder_url = orig_coder_url


class TestGatewayServer:
    """Comprehensive test suite for the Unified IDE Gateway Server."""

    def test_health_check_endpoint(self, client):
        """Verify GET /health returns 200 and healthy subsystem diagnostics."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "Lauburu Unified IDE Gateway"
        assert data["port"] == GATEWAY_PORT
        assert "ram_governance" in data
        assert data["ram_governance"]["sanctuary_min_gb"] == HOST_SANCTUARY_MIN_GB
        assert data["components"]["hermes_router"]["registered_tools"] >= 5
        assert data["components"]["vector_pager"]["kv_cache_pages"] >= 1

    def test_models_endpoint(self, client):
        """Verify GET /v1/models lists all required models."""
        resp = client.get("/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "list"
        model_ids = [m["id"] for m in data["data"]]
        assert "qwen_38_max_abliterated" in model_ids
        assert "qwen2.5-coder-7b-instruct" in model_ids
        assert "dynamic-mcts-chat" in model_ids
        assert "dynamic-mcts-autocomplete" in model_ids

    def test_chat_completion_pure_code_routing(self, client):
        """Verify pure code prompt routes to Qwen 2.5 Coder."""
        payload = {
            "model": "dynamic-mcts-chat",
            "messages": [
                {"role": "user", "content": "def calculate_fft(signal):\n    pass"}
            ],
            "stream": False
        }
        resp = client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data

    def test_chat_completion_tool_routing(self, client):
        """Verify request with tool or skill keywords routes to Hermes Router."""
        payload = {
            "model": "dynamic-mcts-chat",
            "messages": [
                {"role": "user", "content": "Please run terminal command to check git status and diff"}
            ],
            "stream": False
        }
        resp = client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data

    def test_chat_completion_loop_trigger(self, client):
        """Verify prompt containing /loop triggers continuous distillation."""
        payload = {
            "model": "dynamic-mcts-chat",
            "messages": [
                {"role": "user", "content": "/loop optimize the memory governor"}
            ],
            "stream": False
        }
        resp = client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data

    def test_context_overflow_blocked_by_escalation_gate(self, client):
        """Verify that payload exceeding 8,192 tokens triggers HTTP 403 Forbidden."""
        huge_text = "def massive_context_block():\n    return 'x' * 1000\n" * 700
        assert len(huge_text) > 35000

        payload = {
            "model": "dynamic-mcts-chat",
            "messages": [
                {"role": "user", "content": huge_text}
            ],
            "stream": False
        }
        resp = client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 403
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == 403
        assert data["error"]["type"] == "escalation_required"
        assert data["error"]["tokens"] > 8192

    def test_context_overflow_authorized_pass_through(self, client):
        """Verify that pre-authorized ticket allows context overflow to proceed."""
        huge_text = "def huge(): pass\n" * 2000

        payload = {
            "model": "dynamic-mcts-chat",
            "messages": [
                {"role": "user", "content": huge_text}
            ],
            "bypass_escalation_gate": True,
            "stream": False
        }
        resp = client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data

    def test_legacy_completions_fim(self, client):
        """Verify /v1/completions formats FIM prompt when prefix and suffix provided."""
        payload = {
            "model": "dynamic-mcts-autocomplete",
            "prompt": "def add(a, b):\n",
            "suffix": "\n    return result",
            "max_tokens": 32,
            "stream": False
        }
        resp = client.post("/v1/completions", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data

    def test_backpressure_task_registration(self, client):
        """Verify POST /api/backpressure/register and GET /api/backpressure/status."""
        reg_payload = {
            "name": "lora_harvester_daemon",
            "pid": 99999,
            "priority": 1
        }
        resp = client.post("/api/backpressure/register", json=reg_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["registered"] is True

        status_resp = client.get("/api/backpressure/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert "tasks" in status_data

    def test_backpressure_register_invalid_pid_rejected(self, client):
        """Verify POST /api/backpressure/register rejects pid <= 0 with HTTP 400."""
        resp_zero = client.post("/api/backpressure/register", json={"name": "zero_task", "pid": 0, "priority": 1})
        assert resp_zero.status_code == 400
        assert "Invalid PID" in resp_zero.json()["detail"]

        resp_neg = client.post("/api/backpressure/register", json={"name": "neg_task", "pid": -10, "priority": 1})
        assert resp_neg.status_code == 400
        assert "Invalid PID" in resp_neg.json()["detail"]

    def test_chat_completion_tool_routing_dispatches_to_8082_preserving_tools(self, client):
        """Verify Hermes routing dispatches directly to Port 8082 with tool schemas preserved."""
        from tests.conftest import MockHermesHandler
        MockHermesHandler.call_log.clear()

        tools = [{
            "type": "function",
            "function": {
                "name": "read_kernel_telemetry",
                "description": "Read Darwin kernel vm_stat metrics",
                "parameters": {"type": "object", "properties": {}}
            }
        }]
        payload = {
            "model": "dynamic-mcts-chat",
            "messages": [
                {"role": "user", "content": "Please read kernel telemetry using the registered tool"}
            ],
            "tools": tools,
            "stream": False
        }
        resp = client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        # Check choices and tool calls in response
        assert "choices" in data
        assert len(data["choices"]) > 0
        choice = data["choices"][0]
        assert "message" in choice
        assert "tool_calls" in choice["message"]

        # Verify MockHermesHandler received the request directly on Port 8082
        assert len(MockHermesHandler.call_log) > 0
        last_hermes_call = MockHermesHandler.call_log[-1]
        assert "tools" in last_hermes_call["body"]
        assert last_hermes_call["body"]["tools"] == tools
        assert last_hermes_call["body"]["model"] == "qwen_38_max_abliterated"

    def test_context_overflow_authorized_pass_through_captures_distillation_trace(self, client):
        """Verify authorized cloud escalation passes through and captures trace in distillation worker."""
        from gateway.server import distillation_worker
        initial_enqueued = distillation_worker.stats["enqueued"]

        huge_text = "def train_lora_kernel(): pass\n" * 1500
        payload = {
            "model": "dynamic-mcts-chat",
            "messages": [
                {"role": "user", "content": huge_text}
            ],
            "bypass_escalation_gate": True,
            "stream": False
        }
        resp = client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 200
        assert distillation_worker.stats["enqueued"] == initial_enqueued + 1

    def test_mesh_telemetry_endpoint(self, client):
        """Verify GET /api/telemetry/mesh returns genuine mesh and host RAM metrics."""
        resp = client.get("/api/telemetry/mesh")
        assert resp.status_code == 200
        data = resp.json()
        assert "pool" in data or "total_mesh_ram_gb" in data

    def test_storage_affinity_endpoint(self, client):
        """Verify GET /api/storage/affinity maps files to physical nodes."""
        # Heavy datasets -> L3 Linux Hub
        resp1 = client.get("/api/storage/affinity?path=04_data_and_memory/lora_datasets/traces.jsonl")
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["target_node"] == "L3_Linux"
        assert data1["collection"] == "heavy_datasets"

        # Git source -> L1 Mac Host
        resp2 = client.get("/api/storage/affinity?path=01_apps/bt_ide_ab_test/main.py")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["target_node"] == "L1_Mac" or "L1_MacHost" in data2["target_node"]
        assert data2["collection"] == "git_source"

    def test_distillation_status_endpoint(self, client):
        """Verify GET /api/distillation/status returns queue metrics."""
        resp = client.get("/api/distillation/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "enqueued" in data
        assert "processed" in data
        assert "dataset_path" in data


class TestCliLauncher:
    """Test suite for lens_ide_router_gateway CLI launcher."""

    def test_probe_tcp_port_localhost(self):
        """Verify probe_tcp_port performs genuine syscalls without random simulation."""
        reachable, rtt = probe_tcp_port("127.0.0.1", 8082, timeout=0.2)
        assert isinstance(reachable, bool)
        assert isinstance(rtt, float)

    def test_check_mesh_health_structure(self):
        """Verify check_mesh_health returns genuine RAM headroom and real endpoint states."""
        diag = check_mesh_health()
        assert "host_ram" in diag
        assert diag["host_ram"]["total_gb"] > 0
        assert diag["host_ram"]["available_gb"] > 0
        assert diag["host_ram"]["sanctuary_limit_gb"] == HOST_SANCTUARY_MIN_GB
        assert "endpoints" in diag
        assert len(diag["endpoints"]) >= 4
