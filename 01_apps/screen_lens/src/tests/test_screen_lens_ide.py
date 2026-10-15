import pytest
import sys
import os
import json
import urllib.request
from pathlib import Path

# Add src and ide to sys.path
IDE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ide"))
sys.path.insert(0, IDE_DIR)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lens_monorepo_roi_engine import MonorepoROIEngine, PrioritizedTask
from lens_workspace_cloud_hub import LensWorkspaceCloudHub
from screen_lens_tui_ide import ScreenLensTUIIDE
from screen_lens_notebook_ide import ScreenLensNotebookIDE


def test_monorepo_roi_engine_scanning():
    engine = MonorepoROIEngine()
    tasks = engine.scan_and_prioritize()
    
    assert len(tasks) >= 4, f"Expected at least 4 tasks, got {len(tasks)}"
    
    # Verify tasks are sorted descending by ROI
    roi_scores = [t.roi_score for t in tasks]
    assert roi_scores == sorted(roi_scores, reverse=True), "Tasks must be sorted descending by ROI"
    
    # Verify mandatory fields
    for t in tasks:
        assert t.task_id.startswith("task_")
        assert t.impact_score > 0
        assert t.savings_factor > 0
        assert t.assigned_model != ""
        assert t.mesh_host != ""


def test_roi_formula_math():
    engine = MonorepoROIEngine()
    
    # Test high speedup task (e.g. 1381.8x)
    roi_high = engine.calculate_roi(impact=90.0, savings=9.0, speedup=1381.8, complexity=2.0, vram_penalty=0.0)
    assert roi_high > 1000.0
    
    # Test moderate speedup task (e.g. 20x)
    roi_mod = engine.calculate_roi(impact=85.0, savings=5.0, speedup=20.0, complexity=2.0, vram_penalty=0.0)
    assert 200.0 < roi_mod < 400.0


def test_distributed_sharding_probing():
    hub = LensWorkspaceCloudHub()
    shards = hub.probe_distributed_sharding()
    
    assert len(shards) >= 6
    names = [s.node_name for s in shards]
    assert "L1_Mac_Node_Local" in names
    assert "L3_Linux_Mini_RPC" in names
    assert "L6_Pixel_10_Pro_XL" in names

    # Local host socket should respond very fast
    local_shard = next(s for s in shards if s.node_name == "L1_Mac_Node_Local")
    assert local_shard.rtt_ms < 100.0


def test_google_workspace_alerts(tmp_path, monkeypatch):
    hub = LensWorkspaceCloudHub()
    
    # Add test alert
    hub.add_workspace_alert(
        account="lauburu@lauburugrappling.com",
        sender="pytest_agent",
        subject="Test Alert Execution",
        priority="HIGH"
    )
    
    alerts = hub.get_google_workspace_alerts(limit=10)
    assert len(alerts) > 0
    assert any(a.get("subject") == "Test Alert Execution" for a in alerts)


def test_google_cloud_quota_pacing():
    hub = LensWorkspaceCloudHub()
    quota = hub.get_google_cloud_quota_status()
    
    assert quota.daily_quota_rpd == 1500
    assert quota.remaining_today >= 0
    assert quota.cadence_rpm > 0.0
    assert quota.reset_hours_remaining > 0.0


def test_tui_ide_plain_rendering():
    ide = ScreenLensTUIIDE()
    ide.refresh()
    rendered = ide.render_plain()
    
    assert "SCREEN LENS SOVEREIGN: TUI IDE CONSOLE" in rendered
    assert "DISTRIBUTED AI TENSOR SHARDING" in rendered
    assert "GOOGLE CLOUD FREE TIER" in rendered
    assert "HIGHEST-ROI MONOREPO TASK QUEUE" in rendered


def test_tui_ide_top_task_execution():
    ide = ScreenLensTUIIDE()
    ide.refresh()
    res = ide.execute_top_task()
    
    assert res["status"] == "SUCCESS"
    assert "task" in res


def test_notebook_ide_http_api():
    # Use isolated port 4018 to avoid collisions
    test_port = 4018
    ide = ScreenLensNotebookIDE(port=test_port)
    ide.start(blocking=False)
    
    try:
        # Test /api/status
        req = urllib.request.urlopen(f"http://127.0.0.1:{test_port}/api/status", timeout=4)
        assert req.status == 200
        data = json.loads(req.read().decode("utf-8"))
        assert data["status"] == "HEALTHY"
        assert len(data["highest_roi_tasks"]) >= 4
        assert len(data["sharding_nodes"]) >= 6

        # Test /api/tasks
        req_tasks = urllib.request.urlopen(f"http://127.0.0.1:{test_port}/api/tasks", timeout=4)
        assert req_tasks.status == 200
        data_tasks = json.loads(req_tasks.read().decode("utf-8"))
        assert len(data_tasks["tasks"]) >= 4

        # Test /api/execute
        exec_req = urllib.request.Request(
            f"http://127.0.0.1:{test_port}/api/execute",
            data=json.dumps({"task_id": "top"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        exec_res = urllib.request.urlopen(exec_req, timeout=4)
        assert exec_res.status == 200
        exec_data = json.loads(exec_res.read().decode("utf-8"))
        assert exec_data["status"] == "SUCCESS"

        # Test UI HTML page
        req_ui = urllib.request.urlopen(f"http://127.0.0.1:{test_port}/", timeout=4)
        assert req_ui.status == 200
        html = req_ui.read().decode("utf-8")
        assert "Screen Lens Sovereign: Reactive Notebook IDE Studio" in html
    finally:
        ide.stop()
