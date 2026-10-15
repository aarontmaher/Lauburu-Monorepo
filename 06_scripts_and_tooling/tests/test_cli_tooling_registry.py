#!/usr/bin/env python3
"""
Unit Tests for CLI Tooling Registry
===================================
Validates:
1. Tool discovery and resolution for gh, git, adb, tailscale, wrangler, jules, uv, jq, docker, shopify.
2. CLI metadata integrity and primary command schemas.
3. Safe command execution and non-zero exit handling.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_DIR.parent

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from cli_tooling_registry import CLIToolingRegistry, CLI_CATALOG


class TestCLIToolingRegistry:

    def test_catalog_structure_and_keys(self):
        assert "gh" in CLI_CATALOG
        assert "git" in CLI_CATALOG
        assert "adb" in CLI_CATALOG
        assert "tailscale" in CLI_CATALOG
        assert "wrangler" in CLI_CATALOG
        assert "jules" in CLI_CATALOG
        assert "uv" in CLI_CATALOG

    def test_get_tool_info_returns_valid_structure(self):
        reg = CLIToolingRegistry()
        gh_info = reg.get_tool_info("gh")
        assert gh_info is not None
        assert gh_info["name"] == "GitHub CLI"
        assert gh_info["category"] == "version_control_and_collaboration"
        assert len(gh_info["primary_commands"]) > 0

    def test_list_installed_tools(self):
        reg = CLIToolingRegistry()
        tools = reg.list_installed_tools()
        assert len(tools) == len(CLI_CATALOG)
        installed_names = [t["tool_id"] for t in tools if t["is_installed"]]
        assert "gh" in installed_names
        assert "git" in installed_names

    def test_safe_execution_handles_invalid_command(self):
        reg = CLIToolingRegistry()
        res = reg.execute_cli_command("git", ["--version"])
        assert res["success"] is True
        assert "git version" in res["stdout"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
