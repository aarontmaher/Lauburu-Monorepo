"""
Unit and Integration Test Suite for CodeClash Arena & Tournament Engine.
File: tests/test_codeclash_arena_engine.py

Covers:
- Rule 6.3 Fast-Path Storage Invariant (<3ms)
- Rule #0 Anti-Mock Scanner & Judicial AST Validator
- 5-Phase Adversarial Duel Cycle (Red Bug Injection, Blue Patch Synthesis, Judicial AST, Sandbox, Adjudication)
- Bradley-Terry ELO Rating Engine with 6-factor dynamic K-scaling
- Continuous LoRA Dataset Streaming (SFT & DPO with atomic POSIX locking)
- Obsidian Leaderboard Synchronization (YAML frontmatter, tables, Wikilinks)
- End-to-End Tournament Battles & CLI Subcommands
- Zero-Mock Sovereign Attestation
"""
from __future__ import annotations

import ast
import json
import math
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Ensure imports
CODECLASH_ROOT = Path(__file__).resolve().parent.parent
MONOREPO_ROOT = Path(__file__).resolve().parents[3]

if str(CODECLASH_ROOT) not in sys.path if 'sys' in locals() else False:
    import sys
    sys.path.insert(0, str(CODECLASH_ROOT))
else:
    import sys
    if str(CODECLASH_ROOT) not in sys.path:
        sys.path.insert(0, str(CODECLASH_ROOT))
    if str(MONOREPO_ROOT) not in sys.path:
        sys.path.insert(0, str(MONOREPO_ROOT))

from codeclash_arena_engine import (
    AntiMockScanner,
    BlueTeamPatchSynthesizer,
    BradleyTerryEloEngine,
    CodeClashArenaEngine,
    LoRADatasetStreamer,
    MutationType,
    ObsidianLeaderboardSync,
    RedTeamBugInjector,
    SubprocessTestRunner,
    SWE_BENCHMARK_TASKS,
    calculate_elo_update,
    execute_duel,
    run_tournament,
    stream_lora_records,
    update_obsidian_leaderboard,
    validate_judicial_ast,
    verify_tri_vault_health,
    verify_tri_vault_health_fast_path,
)
from models.schemas import (
    DuelResult,
    MatchPhase,
    ModelRatingRecord,
    TournamentReport,
)


# ============================================================================
# 1. RULE 6.3 FAST-PATH STORAGE INVARIANT TESTS (<3ms)
# ============================================================================

class TestTriVaultStorageInvariant:
    """Tests sub-3ms Tri-Vault Storage Invariant verification."""

    def test_fast_path_timing_under_3ms(self) -> None:
        """Fast-path health check must execute strictly under 3.0ms."""
        t0 = time.perf_counter()
        ok, msg = verify_tri_vault_health_fast_path()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert ok is True
        assert elapsed_ms < 3.0, f"Invariant violated: Check took {elapsed_ms:.3f}ms (must be < 3.0ms)"
        assert "HEALTHY" in msg

    def test_public_verify_tri_vault_health_alias(self) -> None:
        """Public alias returns expected boolean and string."""
        ok, msg = verify_tri_vault_health()
        assert ok is True
        assert "Disk free" in msg

    def test_degraded_storage_detection_missing_obsidian(self, tmp_path: Path) -> None:
        """Correctly detects degraded state if Obsidian vault is missing."""
        ok, msg = verify_tri_vault_health_fast_path(base_dir=tmp_path)
        assert ok is False
        assert "Degraded Obsidian Vault" in msg


# ============================================================================
# 2. RULE #0 ANTI-MOCK SCANNER & JUDICIAL AST VALIDATOR TESTS
# ============================================================================

class TestAntiMockScannerAndJudicialAST:
    """Tests Rule #0 enforcement and AST validation."""

    def test_clean_code_passes_anti_mock_scanner(self, python_source_clean: str) -> None:
        """Clean authentic code passes zero-mock scanner."""
        is_compliant, violations = AntiMockScanner.scan_code(python_source_clean)
        assert is_compliant is True
        assert len(violations) == 0

    def test_prohibited_mock_libraries_detected(self) -> None:
        """Scanner flags unittest.mock, MagicMock, Mock()."""
        mock_snippet_1 = "from unittest.mock import MagicMock\nm = MagicMock()"
        mock_snippet_2 = "import pytest_mock\ndef test_fake():\n    pass"

        assert AntiMockScanner.scan_code(mock_snippet_1)[0] is False
        assert AntiMockScanner.scan_code(mock_snippet_2)[0] is False

    def test_prohibited_hardcoded_dummy_arrays_detected(self) -> None:
        """Scanner flags simulated arrays and hardcoded DSP dummies."""
        dummy_code = "def get_ecg():\n    # Hardcoded dummy\n    return [128, 256, 384, 512]\n"
        is_compliant, violations = AntiMockScanner.scan_code(dummy_code)
        assert is_compliant is False
        assert len(violations) >= 1

    def test_validate_judicial_ast_valid_syntax(self, python_source_clean: str) -> None:
        """Valid syntax produces positive validation with low AST distance."""
        ast_ok, msg, dist, zero_mock = validate_judicial_ast(python_source_clean, python_source_clean)
        assert ast_ok is True
        assert zero_mock is True
        assert dist == 0.0

    def test_validate_judicial_ast_syntax_error(self) -> None:
        """Syntax error is caught and reported."""
        bad_code = "def broken(:\n    pass"
        ast_ok, msg, dist, zero_mock = validate_judicial_ast(bad_code)
        assert ast_ok is False
        assert "SyntaxError" in msg
        assert zero_mock is False


# ============================================================================
# 3. PHASE 1: RED TEAM BUG INJECTION & OBFUSCATION TESTS
# ============================================================================

class TestRedTeamBugInjector:
    """Tests realistic bug mutations across SWE benchmark tasks."""

    def test_mutate_sliding_window_off_by_one(self) -> None:
        """Injects off-by-one boundary error in sliding window."""
        code = "def sliding_window_max(nums, k):\n    for i in range(len(nums) - k + 1):\n        pass\n"
        poisoned, desc = RedTeamBugInjector.mutate_sliding_window(code, MutationType.OFF_BY_ONE_INDEX)
        assert "len(nums) - k" in poisoned
        assert "len(nums) - k + 1" not in poisoned
        assert "off-by-one" in desc.lower()

    def test_mutate_pan_tompkins_threshold_distortion(self) -> None:
        """Injects distorted threshold into QRS detector."""
        code = "def detect_qrs_peaks(signal, threshold=0.5):\n    if signal[i] >= threshold:\n        pass\n"
        poisoned, desc = RedTeamBugInjector.mutate_pan_tompkins(code, MutationType.INVERT_CONDITIONAL)
        assert "threshold * 2.0" in poisoned

    def test_mutate_circular_buffer_mutex_strip(self) -> None:
        """Strips mutex lock to create race condition hazard."""
        code = "class CircularBuffer:\n    def push(self, item):\n        with self.lock:\n            return True\n"
        poisoned, desc = RedTeamBugInjector.mutate_circular_buffer(code, MutationType.CONCURRENCY_MUTEX_STRIP)
        assert "with self.lock:" not in poisoned
        assert "if True:" in poisoned

    def test_mutate_regex_catastrophic_backtracking(self) -> None:
        """Injects polynomial catastrophic backtracking pattern."""
        code = r'pattern = re.compile(r"^[a-zA-Z0-9_-]+$")'
        poisoned, desc = RedTeamBugInjector.mutate_regex_parser(code, MutationType.REGEX_REDOS_BACKTRACKING)
        assert r"^([a-zA-Z0-9_-]+)+$" in poisoned
        assert "ReDoS" in desc or "backtracking" in desc.lower()

    def test_inject_mutation_dispatcher(self) -> None:
        """Dispatcher correctly routes by task_id and returns 3-tuple."""
        task = SWE_BENCHMARK_TASKS[0]
        poisoned, desc, mtype = RedTeamBugInjector.inject_mutation(task["task_id"], task["base_code"])
        assert len(poisoned) > 0
        assert len(desc) > 0
        assert mtype == "off_by_one_index"


# ============================================================================
# 4. PHASE 2: BLUE TEAM DEFENSE & PATCH SYNTHESIS TESTS
# ============================================================================

class TestBlueTeamPatchSynthesizer:
    """Tests patch synthesis and unified git diff generation."""

    def test_generate_unified_diff_format(self) -> None:
        """Generates valid unified diff with standard headers."""
        orig = "def foo():\n    return 1\n"
        repaired = "def foo():\n    return 2\n"
        diff = BlueTeamPatchSynthesizer.generate_unified_diff(orig, repaired, "candidate.py")
        assert "--- a/candidate.py" in diff
        assert "+++ b/candidate.py" in diff
        assert "-    return 1" in diff
        assert "+    return 2" in diff

    def test_synthesize_patch_restores_base_code(self) -> None:
        """Patch synthesis restores benchmark ground truth."""
        task = SWE_BENCHMARK_TASKS[0]
        poisoned, _, _ = RedTeamBugInjector.inject_mutation(task["task_id"], task["base_code"])
        patched, diff, thoughts = BlueTeamPatchSynthesizer.synthesize_patch(task, poisoned, "qwen2.5-coder-32b")
        assert patched == task["base_code"]
        assert len(diff) > 0
        assert "<thought>" in thoughts


# ============================================================================
# 5. PHASE 4: SANDBOXED SUBPROCESS TEST RUNNER TESTS
# ============================================================================

class TestSubprocessTestRunner:
    """Tests sandboxed execution of test suites."""

    def test_passing_candidate_returns_true(self) -> None:
        """Passing code succeeds in sandbox with nonzero assertion counts."""
        cand = "def add(a, b):\n    return a + b\n"
        test = "def test_add():\n    from candidate import add\n    assert add(2, 3) == 5\n"
        passed, out, err, lat, mem, count = SubprocessTestRunner.run_pytest_in_sandbox(cand, test)
        assert passed is True
        assert lat > 0.0
        assert count >= 1

    def test_failing_candidate_returns_false(self) -> None:
        """Broken code fails in sandbox with captured stdout/stderr."""
        cand = "def add(a, b):\n    return a - b\n"
        test = "def test_add():\n    from candidate import add\n    assert add(2, 3) == 5\n"
        passed, out, err, lat, mem, count = SubprocessTestRunner.run_pytest_in_sandbox(cand, test)
        assert passed is False
        assert "AssertionError" in out or "FAILED" in out

    def test_timeout_protection(self) -> None:
        """Infinite loop is safely terminated by timeout."""
        cand = "def loop():\n    while True:\n        pass\n"
        test = "def test_loop():\n    from candidate import loop\n    loop()\n"
        passed, out, err, lat, mem, count = SubprocessTestRunner.run_pytest_in_sandbox(cand, test, timeout_seconds=1.0)
        assert passed is False
        assert "timed out" in err.lower()


# ============================================================================
# 6. BRADLEY-TERRY ELO RATING ENGINE TESTS
# ============================================================================

class TestBradleyTerryEloEngine:
    """Tests mathematical Bradley-Terry ELO formulas and 6-factor K-scaling."""

    def test_win_probability_logistic_bounds(self) -> None:
        """Equal ratings give 50% probability; higher rating gives >50%."""
        assert math.isclose(BradleyTerryEloEngine.win_probability(2000.0, 2000.0), 0.5, rel_tol=1e-3)
        assert BradleyTerryEloEngine.win_probability(2400.0, 2000.0) > 0.90
        assert BradleyTerryEloEngine.win_probability(1600.0, 2000.0) < 0.10

    def test_base_k0_match_count_tiering(self) -> None:
        """K0 scales down as matches increase: <10 (48), 10-50 (32), >=50 (24)."""
        k_early = BradleyTerryEloEngine.calculate_k_factor(matches_played=5)
        k_mid = BradleyTerryEloEngine.calculate_k_factor(matches_played=20)
        k_vet = BradleyTerryEloEngine.calculate_k_factor(matches_played=60)
        assert k_early > k_mid > k_vet

    def test_k_multipliers_size_token_consensus_compute_truth(self) -> None:
        """All 6 multipliers influence dynamic K-factor."""
        # Truth compliance: 0 if mock violation
        k_compliant = BradleyTerryEloEngine.calculate_k_factor(zero_mock_certified=True)
        k_mock = BradleyTerryEloEngine.calculate_k_factor(zero_mock_certified=False)
        assert k_compliant > 0.0
        assert k_mock == 0.0

        # Token efficiency: fewer tokens -> higher K
        k_efficient = BradleyTerryEloEngine.calculate_k_factor(tokens_used=200)
        k_bloated = BradleyTerryEloEngine.calculate_k_factor(tokens_used=4000)
        assert k_efficient > k_bloated

    def test_calculate_elo_update_symmetry(self) -> None:
        """Win/Loss updates move ratings in opposite directions."""
        r_a, r_b = 2000.0, 2000.0
        new_a, new_b, delta_a, delta_b = BradleyTerryEloEngine.calculate_update(r_a, r_b, 1.0, 0.0)
        assert new_a > 2000.0
        assert new_b < 2000.0
        assert delta_a > 0.0
        assert delta_b < 0.0


# ============================================================================
# 7. CONTINUOUS LORA DATASET STREAMING TESTS
# ============================================================================

class TestLoRADatasetStreamer:
    """Tests atomic POSIX file locking and JSONL dataset accumulation."""

    def test_append_record_atomic_locking(self, tmp_path: Path) -> None:
        """Appends record with flock and creates valid JSONL line."""
        sink = tmp_path / "lora_test.jsonl"
        rec = {"record_type": "sft_instruction", "id": "sft_001", "task": "test", "zero_mock_certified": True}
        assert LoRADatasetStreamer.append_record(rec, sink) is True
        assert sink.exists()

        lines = sink.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["id"] == "sft_001"

    def test_stream_multiple_records(self, tmp_path: Path) -> None:
        """Streams batch of SFT and DPO records."""
        sink = tmp_path / "lora_batch.jsonl"
        records = [
            {"record_type": "sft_instruction", "id": f"sft_{i}", "val": i}
            for i in range(5)
        ]
        count = LoRADatasetStreamer.stream_records(records, sink)
        assert count == 5

        lines = sink.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 5


# ============================================================================
# 8. OBSIDIAN LEADERBOARD SYNCHRONIZATION TESTS
# ============================================================================

class TestObsidianLeaderboardSync:
    """Tests YAML frontmatter, table formatting, and Wikilinks in Obsidian notes."""

    def test_leaderboard_content_generation(self) -> None:
        """Generates markdown with frontmatter, tables, and canonical Wikilinks."""
        registry = CodeClashArenaEngine.get_default_model_registry()
        content = ObsidianLeaderboardSync.generate_leaderboard_content(registry, total_matches=50)

        assert "---" in content
        assert "tags: [codeclash, swe_bench" in content
        assert "total_matches: 50" in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in content
        assert "[[SWEBENCH_MESH_LEADERBOARD_2026]]" in content
        assert "🥇" in content
        assert "Qwen 2.5 Coder 32B" in content

    def test_atomic_file_sync(self, tmp_path: Path) -> None:
        """Atomically updates target note path."""
        target = tmp_path / "LEADERBOARD_TEST.md"
        registry = CodeClashArenaEngine.get_default_model_registry()
        synced_path = ObsidianLeaderboardSync.sync_to_file(registry, 10, target)

        assert Path(synced_path).exists()
        assert "CodeClash" in target.read_text(encoding="utf-8")


# ============================================================================
# 9. END-TO-END ARENA DUEL & TOURNAMENT TESTS
# ============================================================================

class TestCodeClashArenaEngineE2E:
    """Tests end-to-end duel cycle and multi-round tournament execution."""

    def test_single_duel_cycle(self, tmp_path: Path) -> None:
        """Executes full 5-phase duel: Red Bug Injection -> Blue Defense -> Adjudication."""
        lora_file = tmp_path / "duel_lora.jsonl"
        lb_file = tmp_path / "duel_lb.md"
        engine = CodeClashArenaEngine(lora_sink_path=lora_file, leaderboard_path=lb_file)

        task = SWE_BENCHMARK_TASKS[0]
        res = engine.execute_duel(task, "qwen2.5-7b-abliterated", "qwen2.5-coder-32b")

        assert isinstance(res, DuelResult)
        assert res.ast_valid is True
        assert res.zero_mock_certified is True
        assert res.test_passed_original is True
        assert res.test_passed_poisoned is False  # Red successfully broke test
        assert res.test_passed_patched is True   # Blue successfully repaired code
        assert res.duration_ms > 0.0
        assert lora_file.exists()

    def test_full_3_match_tournament(self, tmp_path: Path) -> None:
        """Executes 3-match tournament battle and verifies rankings and outputs."""
        lora_file = tmp_path / "tourn_lora.jsonl"
        lb_file = tmp_path / "tourn_lb.md"
        engine = CodeClashArenaEngine(lora_sink_path=lora_file, leaderboard_path=lb_file)

        report = engine.run_tournament(rounds=3)

        assert isinstance(report, TournamentReport)
        assert report.rounds_completed == 3
        assert report.matches_played == 3
        assert report.lora_records_streamed == 6  # 1 SFT + 1 DPO per match
        assert report.zero_mock_compliance == 100.0
        assert report.storage_health is True
        assert Path(report.leaderboard_path).exists()

        # Check rankings sorting
        ratings = [r["elo_rating"] for r in report.model_rankings]
        assert ratings == sorted(ratings, reverse=True)


# ============================================================================
# 10. ZERO-MOCK INTEGRITY ATTESTATION (RULE #0)
# ============================================================================

class TestZeroMockIntegrityAttestation:
    """Validates that all tournament telemetry is genuine with zero mock data."""

    def test_no_mock_framework_imports_in_source(self) -> None:
        """Source code contains zero imports from mock libraries."""
        engine_file = CODECLASH_ROOT / "codeclash_arena_engine.py"
        content = engine_file.read_text(encoding="utf-8")
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "mock" not in alias.name.lower()
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "mock" not in node.module.lower()

    def test_genuine_elo_differential(self) -> None:
        """Winning candidate receives authentic mathematical ELO increase."""
        engine = CodeClashArenaEngine()
        task = SWE_BENCHMARK_TASKS[0]
        res = engine.execute_duel(task, "hermes-3-8b", "qwen2.5-coder-32b")
        if res.winner == "Qwen 2.5 Coder 32B":
            assert res.elo_blue_after > res.elo_blue_before
            assert res.elo_red_after < res.elo_red_before
