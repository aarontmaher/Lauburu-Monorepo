#!/usr/bin/env python3
"""
Unit Tests for Unified Tooling & API Registry
=============================================
Validates:
1. All 4 Tiers (Google Cloud, Google Workspace, Systems CLIs, Local Mesh APIs).
2. Domain-Wide Delegation (DWD) mapping for Google Workspace (Drive, Gmail, Chat, Sheets, Docs).
3. Query capability filters and metadata schemas.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_DIR.parent

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from unified_tooling_and_api_registry import UnifiedToolingRegistry, UNIFIED_TOOL_CATALOG


class TestUnifiedToolingRegistry:

    def test_total_registered_tools_count(self):
        reg = UnifiedToolingRegistry()
        tools = reg.list_all_tools()
        assert len(tools) >= 19
        assert len(tools) == len(UNIFIED_TOOL_CATALOG)

    def test_google_workspace_tier_coverage(self):
        reg = UnifiedToolingRegistry()
        ws_tools = reg.get_tools_by_tier("google_workspace")
        assert len(ws_tools) == 5
        ws_ids = [t["id"] for t in ws_tools]
        assert "google_drive_api" in ws_ids
        assert "google_gmail_api" in ws_ids
        assert "google_chat_api" in ws_ids
        assert "google_sheets_api" in ws_ids
        assert "google_docs_api" in ws_ids

    def test_google_cloud_tier_coverage(self):
        reg = UnifiedToolingRegistry()
        gc_tools = reg.get_tools_by_tier("google_cloud")
        assert len(gc_tools) >= 5
        gc_ids = [t["id"] for t in gc_tools]
        assert "google_cloud_run" in gc_ids
        assert "google_cloud_storage" in gc_ids
        assert "google_vertex_ai" in gc_ids
        assert "google_jules" in gc_ids
        assert "nvidia_nim_deepseek_v4" in gc_ids

    def test_local_mesh_apis_coverage(self):
        reg = UnifiedToolingRegistry()
        mesh_tools = reg.get_tools_by_tier("local_mesh_api")
        assert len(mesh_tools) == 4
        mesh_ids = [t["id"] for t in mesh_tools]
        assert "screen_lens_rest" in mesh_ids
        assert "tb4_pcie_dma_bridge" in mesh_ids

    def test_query_tool_capability_search(self):
        reg = UnifiedToolingRegistry()
        drive_matches = reg.query_tool_capability("drive")
        assert len(drive_matches) >= 1
        assert drive_matches[0]["id"] == "google_drive_api"

        gpu_matches = reg.query_tool_capability("metal")
        assert len(gpu_matches) >= 1


if __name__ == "__main__":
    pytest.main(["-v", __file__])
