"""
Tests for Neo Monorepo Project App Graph Service, Bicep ECG HUD, and Obsidian Vault Sync.
Compliant with Rule 0 (Zero-Mock) and Rule 2 (Tri-Vault Storage).
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "01_apps/canonical_port"))

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.neo_project_graph_service import NeoProjectGraphService, OBSIDIAN_GRAPH_FILE

client = TestClient(app)


def test_neo_graph_service_topology():
    """Verify Neo graph returns comprehensive multi-domain catalog."""
    graph = NeoProjectGraphService.get_full_graph()
    summary = graph["summary"]
    nodes = graph["nodes"]
    edges = graph["edges"]

    assert summary["total_nodes"] >= 40
    assert summary["total_edges"] >= 25
    assert len(nodes) == summary["total_nodes"]
    assert len(edges) == summary["total_edges"]

    categories = summary["categories"]
    assert categories["tui"] >= 8
    assert categories["webapp"] >= 8
    assert categories["notebook"] >= 8
    assert categories["node"] >= 8
    assert categories["biometric"] >= 1
    assert categories["storage"] >= 3
    assert categories["commerce"] >= 2
    assert categories["cloud"] >= 1


def test_usb3_bus_detection():
    """Verify authentic hardware detection of USB 3.2 Gen 2 (10 Gbps) bus."""
    usb3 = NeoProjectGraphService._detect_usb3_bus()
    assert usb3["detected"] is True
    assert "USB 3" in usb3["protocol"]
    assert "10 Gbps" in usb3["max_rate"]
    assert "AppleT8132" in usb3["apple_controller"]


def test_bicep_ecg_kamath_filter():
    """Verify Movesense Bicep ECG telemetry with Kamath 20% filter."""
    ecg = NeoProjectGraphService.get_live_bicep_ecg()
    assert ecg["device_name"] == "Movesense 261030002013"
    assert ecg["placement"] == "bicep_strap"
    assert "Kamath 20%" in ecg["dsp_profile"]
    assert "ENGAGED" in ecg["kamath_20_filter"]
    assert ecg["zone"] in [
        "STANDBY",
        "ZONE 1 (Warmup / Recovery)",
        "ZONE 2 (Aerobic Base Endurance)",
        "ZONE 3 (Tempo / Aerobic Power)",
        "ZONE 4 (Lactate Threshold)",
        "ZONE 5 (Anaerobic / VO2 Max)",
    ]


def test_obsidian_vault_graph_sync():
    """Verify Neo synthesizes and synchronizes graph into Obsidian Vault."""
    res = NeoProjectGraphService.sync_graph_to_obsidian()
    assert res["success"] is True
    assert Path(res["vault_path"]).exists()
    assert res["total_nodes"] >= 40

    with open(res["vault_path"], "r", encoding="utf-8") as f:
        content = f.read()

    assert "```mermaid" in content
    assert "graph TD" in content
    assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
    assert "[[01_zero_mock_truth_rule]]" in content
    assert "USB 3.2 Gen 2 (10 Gbps)" in content
    assert "Movesense 261030002013" in content
    assert "bicep_strap" in content


def test_fastapi_graph_endpoints():
    """Verify FastAPI endpoints return 200 OK with authentic payload."""
    res_topo = client.get("/api/v1/graph/topology")
    assert res_topo.status_code == 200
    topo_data = res_topo.json()
    assert topo_data["summary"]["total_nodes"] >= 40

    res_ecg = client.get("/api/v1/biometrics/movesense/live")
    assert res_ecg.status_code == 200
    ecg_data = res_ecg.json()
    assert ecg_data["device_name"] == "Movesense 261030002013"
    assert ecg_data["placement"] == "bicep_strap"

    res_sync = client.post("/api/v1/graph/sync_vault")
    assert res_sync.status_code == 200
    sync_data = res_sync.json()
    assert sync_data["success"] is True
    assert sync_data["total_nodes"] >= 40
