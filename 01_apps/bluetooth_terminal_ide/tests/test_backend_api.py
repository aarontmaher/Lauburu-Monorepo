#!/usr/bin/env python3
"""
Unit and Integration Tests for Lauburu Bluetooth Terminal IDE Backend.
Governed by:
- Rule 0 (Zero-Mock): Authentic endpoint tests against live FastAPI engine.
- Rule 1 (Tri-Proof): Exact process assertions and exit code verification.
"""

import json
import pytest
import httpx
import websockets
import asyncio
import base64
import io
from PIL import Image, ImageDraw

BASE_URL = "http://127.0.0.1:4050"
WS_URL = "ws://127.0.0.1:4050/ws/terminal"

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c

def test_health_endpoint(client):
    """Verifies that the backend is healthy and has indexed the knowledge vault."""
    resp = client.get("/health")
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    data = resp.json()
    assert data.get("status") == "HEALTHY"
    assert data.get("app") == "Lauburu Bluetooth Terminal IDE"
    assert data.get("rag_docs_indexed", 0) >= 1000, "RAG index should contain >1000 docs"
    assert data.get("prima_default") == "http://127.0.0.1:8082"

def test_engine_status_endpoint(client):
    """Verifies that engine status reports default prima.cpp engine."""
    resp = client.get("/api/engine/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("default_engine") == "prima.cpp"
    assert "prima" in data
    assert "devils_advocate" in data

def test_terminal_help_macro(client):
    """Verifies the help macro listing."""
    resp = client.post("/api/terminal/run", json={"command": "help"})
    assert resp.status_code == 200
    out = resp.json().get("output", "")
    assert "Available Macros & Commands" in out
    assert "audit" in out
    assert "prima" in out
    assert "debate" in out

def test_terminal_audit_macro(client):
    """Verifies the audit macro reporting Host Free RAM and Disk."""
    resp = client.post("/api/terminal/run", json={"command": "audit"})
    assert resp.status_code == 200
    out = resp.json().get("output", "")
    assert "LAUBURU HOST SANCTUARY AUDIT" in out
    assert "Host Free RAM:" in out
    assert "ALL SYSTEMS GREEN" in out

def test_terminal_prima_macro(client):
    """Verifies the prima macro returning live daemon telemetry."""
    resp = client.post("/api/terminal/run", json={"command": "prima"})
    assert resp.status_code == 200
    out = resp.json().get("output", "")
    assert "service" in out or "status" in out or "ONLINE" in out

def test_terminal_shell_command_execution(client):
    """Verifies live shell execution on the host."""
    resp = client.post("/api/terminal/run", json={"command": "echo LAUBURU_ZERO_MOCK_TEST_VERIFIED"})
    assert resp.status_code == 200
    out = resp.json().get("output", "")
    assert "LAUBURU_ZERO_MOCK_TEST_VERIFIED" in out

def test_rag_query_endpoint(client):
    """Verifies offline RAG search across the 5,504 indexed markdown documents."""
    resp = client.post("/api/rag/query", json={"query": "zero mock truth rule", "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) > 0
    top = data["results"][0]
    assert "title" in top
    assert "path" in top
    assert "score" in top
    assert top["score"] > 0

def test_rag_chat_endpoint(client):
    """Verifies offline RAG assistant conversation."""
    resp = client.post("/api/rag/chat", json={"prompt": "Summarize rule 1 in 10 words."})
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert len(data["response"]) > 0
    assert "sources" in data

def test_debate_run_endpoint(client):
    """Verifies Tri-Orchestrator AI debate synthesis."""
    resp = client.post("/api/debate/run", json={"topic": "Pipelined Ring Parallelism vs RPC", "rounds": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert "topic" in data
    assert "round1_master" in data
    assert "round2_devils" in data
    assert "round3_cloud" in data
    assert "consensus_score" in data
    assert data["consensus_score"] >= 0.90
    assert "summary" in data

def test_lens_analyze_endpoint(client):
    """Verifies Screen Lens optical analysis endpoint."""
    img = Image.new('RGB', (320, 120), color=(10, 15, 20))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "print('Hello Lauburu Screen Lens')", fill=(0, 255, 128))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    img_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')

    resp = client.post("/api/lens/analyze", json={"image_base64": img_b64, "prompt": "Extract code"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    assert "text" in data
    assert "metadata" in data

@pytest.mark.asyncio
async def test_websocket_pty_streaming():
    """Verifies real-time WebSocket PTY connection and command output streaming."""
    async with websockets.connect(WS_URL, close_timeout=5.0) as ws:
        banner = await asyncio.wait_for(ws.recv(), timeout=5.0)
        assert "LAUBURU BLUETOOTH TERMINAL" in banner

        await ws.send("echo PTY_WEBSOCKET_TEST_PASSED\n")
        
        received_match = False
        for _ in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                if "PTY_WEBSOCKET_TEST_PASSED" in msg:
                    received_match = True
                    break
            except asyncio.TimeoutError:
                break
        assert received_match, "Did not receive echoed PTY output over WebSocket"

@pytest.mark.asyncio
async def test_api_chat_endpoint():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:4050", timeout=20.0) as ac:
        res = await ac.post("/api/chat", json={
            "prompt": "Hello test",
            "use_openrouter": False,
            "use_cloudflare": False
        })
        assert res.status_code == 200
        assert "response" in res.json()
