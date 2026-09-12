#!/usr/bin/env python3
"""
Unit and integration tests for Speculative CLI & Tri-Vault Data Retrieval Engine.
Complies with Rule #0 (Zero-Mock) & Rule #1 (Tri-Proof Empirical Verification).
"""

import os
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling"))

from speculative_cli_data_engine import get_speculative_cli_engine, SpeculativeCliDataEngine


class TestSpeculativeCliDataEngine:
    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = get_speculative_cli_engine()

    def test_speculative_drafter_known_pattern(self):
        draft = self.engine.drafter.draft("check network topology")
        assert draft.speculative_command == "lauburu-network"
        assert "--tree" in draft.suggested_args
        assert draft.safety_rating == "SAFE"
        assert draft.confidence_score >= 0.85
        assert draft.latency_ms > 0

    def test_speculative_drafter_destructive_pattern(self):
        draft = self.engine.drafter.draft("delete all databases and format drive")
        assert draft.safety_rating in ("CAUTION", "REJECTED")
        assert draft.confidence_score < 0.50

    def test_streaming_runner_execution(self):
        receipt = self.engine.runner.execute("echo", ["Lauburu Empirical Verification Exit Code 0"])
        assert receipt.exit_code == 0
        assert receipt.zero_mock_certified is True
        assert len(receipt.stdout_lines) > 0
        assert "Lauburu Empirical Verification Exit Code 0" in receipt.stdout_lines[0]
        assert len(receipt.sha256_receipt) == 64

    def test_tri_vault_retrieval(self):
        res = self.engine.retrieve_data("CANONICAL", source="all")
        assert res["matches_found"] > 0
        assert "records" in res
        assert res["duration_ms"] > 0

    def test_api_key_handler_dry_run(self):
        res = self.engine.handle_api_keys(dry_run=True)
        assert "files_scanned" in res
        assert "credentials_found" in res
        assert "duration_ms" in res
