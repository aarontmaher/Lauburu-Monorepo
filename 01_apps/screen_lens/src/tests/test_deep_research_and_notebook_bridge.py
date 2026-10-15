# -*- coding: utf-8 -*-
import pytest
import sys
import os
from pathlib import Path

root_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.append(str(root_path / "01_apps/screen_lens/src"))
sys.path.append(str(root_path / "06_scripts_and_tooling"))

from integrations.gemini_deep_research_bridge import GeminiDeepResearchBridge
from notebooks.notebook_ai_bridge import NotebookAIBridge
import screen_lens_cli

def test_gemini_deep_research_bridge():
    bridge = GeminiDeepResearchBridge()
    records = bridge.extract_deep_research_records(limit=2)
    assert isinstance(records, list)
    
    # Process and distill cycle
    res = bridge.process_and_distill()
    assert res["status"] in ["DISTILLATION_COMPLETE", "NO_RECORDS_FOUND"]
    if res["status"] == "DISTILLATION_COMPLETE":
        assert res["distilled_records"] > 0
        assert os.path.exists(res["obsidian_synthesis"])
        assert os.path.exists(res["distillation_dataset"])

def test_notebook_ai_bridge():
    bridge = NotebookAIBridge()
    topology = bridge.get_kernel_topology()
    assert "primary_marimo_host" in topology
    assert topology["primary_marimo_host"]["ip"] == "100.101.39.98"
    assert topology["host_sanctuary_protection"]["mac_mini_l1_allowed"] is False
    
    telemetry = bridge.fetch_live_telemetry_snapshot()
    assert "total_captures" in telemetry
    assert telemetry["total_captures"] > 0
    
    synced = bridge.sync_to_obsidian_notebooks()
    assert os.path.exists(synced)

def test_screen_lens_cli_connection():
    conn = screen_lens_cli.get_db_connection()
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM captures;").fetchone()[0]
    assert count > 0
    conn.close()

    pid = screen_lens_cli.get_daemon_pid()
    assert pid is not None and pid > 0
