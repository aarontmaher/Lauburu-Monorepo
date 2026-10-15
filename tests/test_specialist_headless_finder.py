#!/usr/bin/env python3
"""Contract & E2E verification test suite for specialist-headless-finder."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AUTOMATION_DIR = REPO_ROOT / "06_scripts_and_tooling" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

import specialist_finder_tools as compat_tool
import specialist_headless_finder_tools as finder_tool


def test_specialist_status_and_10_node_roster():
    res = finder_tool.execute_finder_action("status", {})
    assert res["status"] == "SUCCESS"
    assert res["exit_code"] == 0
    assert res["host_is_l1_sanctuary"] is True
    assert len(res["mesh_search_nodes"]) == 10
    assert set(res["mesh_search_nodes"]) == {"L1", "L8", "L1b", "L2", "L1a", "L3", "L4", "L6", "L7", "GW"}


def test_specialist_compat_entrypoint():
    proc = subprocess.run(
        [sys.executable, str(AUTOMATION_DIR / "specialist_finder_tools.py"), "status"],
        capture_output=True,
        text=True,
        timeout=5.0,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["status"] == "SUCCESS"
    assert compat_tool.execute_finder_action is finder_tool.execute_finder_action


def test_specialist_edge_cases_and_sanitization():
    # Empty / whitespace paths
    assert finder_tool.finder_reveal_path("")["status"] == "ERROR"
    assert finder_tool.finder_reveal_path("   ")["status"] == "ERROR"
    assert finder_tool.finder_inspect_item("")["status"] == "ERROR"
    assert finder_tool.finder_inspect_item("/nonexistent_path_xyz_999")["status"] == "ERROR"

    # Empty / quote-only queries
    assert finder_tool.finder_spotlight_search("")["status"] == "ERROR"
    assert finder_tool.finder_spotlight_search("   ")["status"] == "ERROR"
    assert finder_tool.finder_mesh_search("")["status"] == "ERROR"
    assert finder_tool.finder_mesh_search("'\"   ")["status"] == "ERROR"

    # Non-dict params & unknown action
    assert finder_tool.execute_finder_action("status", ["not_a_dict"])["exit_code"] == 2  # type: ignore[arg-type]
    assert finder_tool.execute_finder_action("invalid_action", {})["exit_code"] == 2


def test_specialist_inspect_and_l2_selection():
    inspect_res = finder_tool.finder_inspect_item(str(REPO_ROOT / "README.md"))
    assert inspect_res["status"] == "SUCCESS"
    assert inspect_res["size_bytes"] > 1000

    sel_res = finder_tool.finder_get_selection(route_to_l2=True)
    assert sel_res["status"] == "SUCCESS"
    assert sel_res["rule3_l2_routed"] is True


def test_specialist_10_node_mesh_search_and_overflow_guard():
    res = finder_tool.finder_mesh_search("README", max_per_node=3)
    assert res["status"] == "SUCCESS"
    assert res["nodes_queried"] == 10
    assert res["nodes_responded"] >= 8
    assert res["overflow_guard_enforced"] is True


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main(["-v", __file__]))
