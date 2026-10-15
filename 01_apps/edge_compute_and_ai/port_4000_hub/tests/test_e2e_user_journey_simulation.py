import os
import sys
import time
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "01_apps" / "edge_compute_and_ai" / "port_4000_hub"))
sys.path.insert(0, str(REPO_ROOT / "01_apps" / "unified_portal"))

from server import app
from modules.cross_app_rag import CrossAppRAGEngine
from modules.movesense_readiness import MovesenseReadinessEngine
from modules.permissions import PermissionGovernor
from modules.addon_apps import AddonAppsEngine


@pytest.fixture
def client():
    return TestClient(app)

# ==================== Stage 1: Clean Installation & Health Probe ====================

def test_stage_1_app_installation_and_health(client):
    """Simulates app startup immediately post-install."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["healthy", "HEALTHY"]
    assert "port" in data or "mesh_nodes_online" in data

# ==================== Stage 2: Permissions & Device Optimization ====================

def test_stage_2_permissions_and_device_optimization(client):
    """Simulates initial permissions setup and automated device optimization."""
    # 1. Inspect granular OS permissions
    perm_resp = client.get("/api/v1/permissions")
    if perm_resp.status_code == 200:
        perms = perm_resp.json()["permissions"]
        assert len(perms) >= 6
        perm_ids = {p["id"] for p in perms}
        assert "bluetooth_ble" in perm_ids
        assert "screen_capture" in perm_ids

    # 2. Trigger autonomous on-device maintenance
    maint_resp = client.post("/api/edge/maintenance")
    assert maint_resp.status_code == 200
    maint_data = maint_resp.json()
    assert maint_data["status"] == "COMPLETED"
    assert len(maint_data["actions_executed"]) > 0

# ==================== Stage 3: Biometrics & Zero-Mock Telemetry ====================

def test_stage_3_biometrics_readiness_probe(client):
    """Simulates Movesense 512Hz ECG sensor discovery and autonomic readiness probe."""
    readiness = MovesenseReadinessEngine.get_live_readiness()
    assert readiness["heart_rate_bpm"] > 0
    assert readiness["hrv_rmssd_ms"] > 0
    assert readiness["readiness_score"] >= 0 and readiness["readiness_score"] <= 100
    assert "recommendation" in readiness

# ==================== Stage 4: In-App Conversational Micro-RAG ====================

def test_stage_4_conversational_edge_chat():
    """Simulates user asking natural conversational questions to the on-device Edge AI."""
    # 1. Screen Lens & Work Query
    query = "Summarize my screen activity from today and give me my action items."
    chat_result = CrossAppRAGEngine.generate_chat_response(query)
    
    assert chat_result["rag_grounded"] is True
    assert "SmolLM2" in chat_result["model_used"] or "local" in chat_result["model_used"]
    assert len(chat_result["response"]) > 100
    # Must contain direct insights (focus score, deep work, or action items)
    resp_text = chat_result["response"].lower()
    assert "work" in resp_text or "focus" in resp_text or "action" in resp_text

# ==================== Stage 5: High-Complexity Cluster Escalation ====================

def test_stage_5_cluster_escalation_and_distillation(client):
    """Simulates high-complexity request triggering Mesh RPC escalation and Rule #8 distillation."""
    complex_prompt = (
        "Perform a deep architectural refactor of the distributed pipelined-ring tensor sharding algorithm. "
        "Formulate the formal mathematical proof for zero-deadlock asynchronous Ring Attention under heterogeneous "
        "Thunderbolt 4 DMA and WireGuard Tailscale multi-hop network topologies, providing complete POSIX implementations."
    )
    
    chat_resp = client.post("/api/v1/chat", json={"query": complex_prompt, "history": []})
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert "response" in data
    assert len(data["response"]) > 50


# ==================== Stage 6: Downloadable App Store Package Generation ====================

def test_stage_6_app_package_download(client):
    """Simulates downloading standalone application packages from Port 4000 App Store."""
    apps_resp = client.get("/api/apps")
    if apps_resp.status_code == 200:
        apps = apps_resp.json()
        assert len(apps) > 0
        first_app = apps[0]
        assert "id" in first_app
        assert "name" in first_app
