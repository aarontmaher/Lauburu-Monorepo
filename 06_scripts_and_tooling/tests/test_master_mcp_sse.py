#!/usr/bin/env python3
"""
06_scripts_and_tooling/tests/test_master_mcp_sse.py
===================================================
Comprehensive Test Suite for Milestone M4 (R7):
Universal Master MCP Server (Port 9999 SSE) & Gemini Spark Public Bridge.

Validates:
1. Universal Master MCP Server tool manifest (6 canonical tools).
2. JSON-RPC 2.0 protocol handling (initialize, ping, tools/list, tools/call).
3. Tool execution logic & empirical outputs across all 6 mesh tools.
4. MasterMCPServer.handle_sse contract and session queueing.
5. GeminiSparkDaemon.sync_public_tunnel contract & file persistence.
6. FastAPI endpoints (/health, /sse, /messages).
"""

import os
import sys
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure paths on sys.path
TEST_DIR = Path(__file__).resolve().parent
TOOLING_ROOT = TEST_DIR.parent
REPO_ROOT = TOOLING_ROOT.parent
MCP_DIR = TOOLING_ROOT / "lauburu_master_mcp"

for p in [str(REPO_ROOT), str(TOOLING_ROOT), str(MCP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from sse_server import (
    app,
    TOOLS,
    MasterMCPServer,
    handle_jsonrpc,
    execute_tool,
)
from gemini_spark_mcp_daemon import (
    GeminiSparkDaemon,
    sync_active_tunnel_url,
    URL_FILE,
    OBSIDIAN_DOC,
)


class TestMasterMCPServerManifestAndTools:
    """Verifies MCP tools manifest and tool execution engine."""

    def test_mcp_tools_manifest_contains_6_tools(self):
        server = MasterMCPServer()
        tools = server.list_tools()
        assert len(tools) == 6

        tool_names = {t["name"] for t in tools}
        expected_names = {
            "mesh_inference_router",
            "get_mesh_topology_and_health",
            "query_knowledge_graph",
            "run_ai_debate",
            "get_optimal_swarm",
            "get_biometrics_dsp_telemetry",
        }
        assert expected_names.issubset(tool_names)

    def test_execute_mesh_inference_router(self):
        res = execute_tool("mesh_inference_router", {"prompt": "Test prompt routing"})
        assert res["status"] == "SUCCESS"
        assert "llama.cpp" in res["routed_engine"]
        assert res["mesh_latency_ms"] <= 0.30

    def test_execute_get_mesh_topology_and_health(self):
        res = execute_tool("get_mesh_topology_and_health", {})
        assert res["pooled_vram_gb"] == 82.8
        assert res["total_nodes"] >= 7
        assert len(res["nodes"]) >= 7

    def test_execute_get_optimal_swarm(self):
        res = execute_tool("get_optimal_swarm", {})
        assert res["synergy_score"] >= 95.0
        assert "AgentWorld" in res["verification"]

    def test_execute_run_ai_debate(self):
        res = execute_tool("run_ai_debate", {"topic": "Zero-Mock Memory Safety"})
        assert res["status"] == "DEBATE_COMPLETE"
        assert res["consensus_score"] >= 0.95

    def test_execute_get_biometrics_dsp_telemetry(self):
        res = execute_tool("get_biometrics_dsp_telemetry", {})
        assert res["sampling_rate_hz"] == 512
        assert "heart_rate_bpm" in res
        assert res["qrs_f1_score"] >= 0.99


class TestJsonRpcProtocolHandling:
    """Verifies standard MCP JSON-RPC 2.0 message handling."""

    def test_jsonrpc_initialize(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        resp = handle_jsonrpc(req)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert "serverInfo" in resp["result"]
        assert resp["result"]["serverInfo"]["name"] == "lauburu-master-mcp"

    def test_jsonrpc_ping(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
        resp = handle_jsonrpc(req)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 2
        assert resp["result"] == {}

    def test_jsonrpc_tools_list(self):
        req = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
        resp = handle_jsonrpc(req)
        assert len(resp["result"]["tools"]) == 6

    def test_jsonrpc_tools_call(self):
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_biometrics_dsp_telemetry",
                "arguments": {}
            }
        }
        resp = handle_jsonrpc(req)
        assert resp["id"] == 4
        content = resp["result"]["content"]
        assert len(content) == 1
        data = json.loads(content[0]["text"])
        assert data["sampling_rate_hz"] == 512

    def test_jsonrpc_unknown_method(self):
        req = {"jsonrpc": "2.0", "id": 99, "method": "non_existent_method"}
        resp = handle_jsonrpc(req)
        assert "error" in resp
        assert resp["error"]["code"] == -32601


class TestMasterMCPEndpointsAndTunnel:
    """Verifies FastAPI HTTP endpoints and Gemini Spark public reverse tunnel synchronization."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_endpoint(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert data["transport"] == "SSE"
        assert data["tools_count"] == 6

    def test_messages_endpoint_jsonrpc(self, client):
        req = {"jsonrpc": "2.0", "id": 10, "method": "tools/list"}
        res = client.post("/messages", json=req)
        assert res.status_code == 200
        data = res.json()
        assert len(data["result"]["tools"]) == 6

    def test_master_mcp_server_handle_sse_contract(self):
        server = MasterMCPServer()
        endpoint = server.handle_sse("client_test_123")
        assert endpoint == "/messages?sessionId=client_test_123"

    def test_gemini_spark_daemon_sync_public_tunnel(self, tmp_path):
        daemon = GeminiSparkDaemon()
        test_url = "https://lauburu-preview.lhr.life"
        synced = daemon.sync_public_tunnel(test_url)

        assert synced == f"{test_url}/sse"
        assert URL_FILE.exists()
        assert URL_FILE.read_text().strip() == f"{test_url}/sse"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
