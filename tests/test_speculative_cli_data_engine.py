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

    def test_streaming_runner_execution_success(self):
        receipt = self.engine.runner.execute("echo", ["Lauburu Empirical Verification Exit Code 0"])
        assert receipt.exit_code == 0
        assert receipt.zero_mock_certified is True
        assert len(receipt.stdout_lines) > 0
        assert "Lauburu Empirical Verification Exit Code 0" in receipt.stdout_lines[0]
        assert len(receipt.sha256_receipt) == 64

    def test_streaming_runner_execution_failure_not_zero_mock(self):
        # When a command fails with non-zero exit code, zero_mock_certified MUST be False
        receipt = self.engine.runner.execute("ls", ["/non_existent_directory_truth_audit_test_xyz"])
        assert receipt.exit_code != 0
        assert receipt.zero_mock_certified is False
        assert len(receipt.stderr_lines) > 0

    def test_missing_binary_sanity_gate_prevents_circular_crash(self):
        # mosh is not installed: ensure it halts with executed=False rather than crashing with Errno 2
        res = self.engine.speculate_and_execute("mosh")
        assert res["executed"] is False
        assert "not found in PATH" in res["reason"]
        assert "suggestion" in res
        assert "brew install mosh" in res["suggestion"]

    def test_comment_handling_does_not_execute_hash_as_binary(self):
        # Shell comments like '# note' must not be executed as '#' binary
        draft = self.engine.drafter.draft("# Better DNS + dig for mesh health checks")
        assert draft.speculative_command == "echo"
        assert draft.confidence_score == 1.0

    def test_ssh_shorthand_translation(self):
        # Typing root@100.103.212.34 should translate to ssh root@100.103.212.34
        draft = self.engine.drafter.draft("root@100.103.212.34")
        assert draft.speculative_command == "ssh"
        assert "root@100.103.212.34" in draft.suggested_args

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

    def test_storage_health_intent_does_not_draft_heal(self):
        # Regression test: 'storage health' must not draft 'heal' via partial substring matching ('heal' in 'health')
        draft = self.engine.drafter.draft("storage health")
        assert draft.speculative_command != "heal"
        assert draft.speculative_command == "python3"
        assert (
            "Tri-Vault Storage" in str(draft.suggested_args)
            or "shutil" in str(draft.suggested_args)
            or "mesh_storage_and_syncthing_orchestrator.py" in str(draft.suggested_args)
        )
        assert draft.confidence_score >= 0.85

    def test_storage_health_phrase_does_not_draft_heal(self):
        # Phrase with word boundaries: 'check storage health'
        draft = self.engine.drafter.draft("check storage health")
        assert draft.speculative_command != "heal"
        assert draft.speculative_command == "python3"

    def test_heal_intent_drafts_heal(self):
        # 'heal' intent must draft 'heal'
        draft = self.engine.drafter.draft("heal")
        assert draft.speculative_command == "heal"
        assert draft.confidence_score >= 0.85

    def test_status_intent_drafts_network(self):
        # 'status' intent drafts network test
        draft = self.engine.drafter.draft("status")
        assert draft.speculative_command == "lauburu-network"
        assert "--test" in draft.suggested_args

    def test_screen_lens_status_drafts_screen_lens(self):
        draft = self.engine.drafter.draft("screen lens status")
        assert draft.speculative_command == "screen-lens"
        assert "status" in draft.suggested_args
        assert draft.confidence_score >= 0.85

    def test_screen_captures_drafts_screen_lens_latest(self):
        draft = self.engine.drafter.draft("screen captures")
        assert draft.speculative_command == "screen-lens"
        assert "latest" in draft.suggested_args

    def test_screen_query_drafts_screen_lens_query(self):
        draft = self.engine.drafter.draft("screen query terminal")
        assert draft.speculative_command == "screen-lens"
        assert "query" in draft.suggested_args
        assert "terminal" in draft.suggested_args

    def test_screen_lens_lifecycle_drafts(self):
        draft_start = self.engine.drafter.draft("screen lens start")
        assert draft_start.speculative_command == "screen-lens"
        assert "start" in draft_start.suggested_args

        draft_stop = self.engine.drafter.draft("screen lens stop")
        assert draft_stop.speculative_command == "screen-lens"
        assert "stop" in draft_stop.suggested_args

    def test_polyglot_specialist_drafts(self):
        draft_langgo = self.engine.drafter.draft("/polyglot-go-bubbletea-specialist")
        assert draft_langgo.speculative_command == "python3"
        assert "specialists" in draft_langgo.suggested_args
        assert "langgo" in draft_langgo.suggested_args

        draft_nl = self.engine.drafter.draft(
            "integrate polyglot specialist skills into langgo pycharm intellij chromium and bt-serial"
        )
        assert draft_nl.speculative_command == "python3"
        assert "specialists" in draft_nl.suggested_args
        assert "all" in draft_nl.suggested_args


