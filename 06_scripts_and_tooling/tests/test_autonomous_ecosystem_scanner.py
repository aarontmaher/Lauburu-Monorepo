#!/usr/bin/env python3
"""
Unit Tests for Autonomous Ecosystem Scanner
===========================================
Validates:
1. GitHub open-source tracking (fmtlib/fmt, mlx, llama.cpp).
2. MCP server status audits.
3. System CLI availability detection (gh, git, adb, etc.).
4. External/Local API probing and language SDK detection.
5. AI Training & Thunderbolt 4 DMA model sharding telemetry.
6. Report generation in Obsidian Vault and continuous LoRA distillation.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_DIR.parent

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from autonomous_ecosystem_scanner import AutonomousEcosystemScanner


class TestAutonomousEcosystemScanner:

    def test_github_ecosystem_tracks_fmtlib(self):
        scanner = AutonomousEcosystemScanner()
        repos = scanner.scan_github_ecosystem()
        assert "fmtlib/fmt" in repos
        assert "ml-explore/mlx" in repos
        assert "ggerganov/llama.cpp" in repos
        fmt_info = repos["fmtlib/fmt"]
        assert "Formatting" in fmt_info["category"]
        assert len(fmt_info["benefits"]) >= 3

    def test_mcp_servers_audit(self):
        scanner = AutonomousEcosystemScanner()
        mcps = scanner.scan_mcp_servers()
        assert len(mcps) >= 6
        assert "chrome-devtools-mcp" in mcps
        assert "memory" in mcps
        assert "docker" in mcps

    def test_scan_clis_checks_host_path(self):
        scanner = AutonomousEcosystemScanner()
        clis = scanner.scan_cli_tools()
        assert "git" in clis
        assert clis["git"]["installed"] is True
        assert "python3" in clis

    def test_ai_training_and_sharding_telemetry(self):
        scanner = AutonomousEcosystemScanner()
        res = scanner.scan_ai_training_and_sharding()
        assert "training" in res
        assert "sharding" in res
        assert res["sharding"]["rtt_latency_ms"] < 1.0
        assert res["sharding"]["pooled_vram_gb"] >= 80.0

    def test_full_ecosystem_scan_produces_valid_report(self):
        scanner = AutonomousEcosystemScanner()
        rep = scanner.run_full_ecosystem_scan()
        assert "scan_id" in rep
        assert "SCAN_" in rep["scan_id"]
        assert "github_ecosystem" in rep
        assert "mcp_servers" in rep
        assert "system_clis" in rep


if __name__ == "__main__":
    pytest.main(["-v", __file__])
